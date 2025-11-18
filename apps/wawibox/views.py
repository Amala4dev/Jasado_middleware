import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.conf import settings
from django.urls import reverse
from datetime import datetime
from types import SimpleNamespace
import time
import os
import re
import datetime
import os
from django.utils import timezone
from django.db import transaction
from django.utils.timezone import now
from decimal import Decimal
from utils import (
    ftps_connection,
    parse_ftp_file_to_model,
    send_email,
    validate_field_maps,
    delete_all_files,
)
from .utils import (
    WawiBoxLog,
    export_wawibox_product_data_to_csv,
    extract_date_from_wawibox_filename,
)
from django.http import JsonResponse, HttpResponse
from apps.core.models import (
    TaskStatus,
    ExportTask,
    BlockedProduct,
    AdditionalMasterData,
    DynamicPrice,
)
from apps.gls.models import (
    GLSMasterData,
    GLSStockLevel,
)
from .mapping import WAWIBOX_DATA_FIELD_MAPS
from .models import (
    WawiboxProduct,
    WawiboxCompetitorPrice,
    WawiboxProductUpdate,
)

# Constants
WAWIBOX_FTP_HOST = settings.WAWIBOX_FTP_HOST
WAWIBOX_FTP_USER = settings.WAWIBOX_FTP_USER
WAWIBOX_FTP_PASSWORD = settings.WAWIBOX_FTP_PASSWORD
WAWIBOX_FTP_PORT = settings.WAWIBOX_FTP_PORT
WAWIBOX_FTP_PATH_DOWNLOADS = settings.WAWIBOX_FTP_PATH_DOWNLOADS
WAWIBOX_FTP_PATH_UPLOADS = settings.WAWIBOX_FTP_PATH_UPLOADS
WAWIBOX_DOWNLOAD_PATH = settings.WAWIBOX_DOWNLOAD_PATH
WAWIBOX_DOWNLOAD_FILES_PATTERNS = settings.WAWIBOX_DOWNLOAD_FILES_PATTERNS


def download_wawibox_files():
    is_completed = False

    try:
        # should_run = TaskStatus.should_run(TaskStatus.DOWNLOAD_FILES_WAWIBOX)
        should_run = 1
        if should_run:
            with ftps_connection(
                WAWIBOX_FTP_HOST,
                WAWIBOX_FTP_USER,
                WAWIBOX_FTP_PASSWORD,
                port=WAWIBOX_FTP_PORT,
            ) as ftp:

                ftp.change_dir(WAWIBOX_FTP_PATH_DOWNLOADS)

                raw_lines = []
                ftp.ftps.retrlines("LIST", raw_lines.append)

                filenames = [line.split()[-1] for line in raw_lines]
                file_name_patterns = tuple(
                    p.lower() for p in WAWIBOX_DOWNLOAD_FILES_PATTERNS
                )

                for pattern in file_name_patterns:
                    dated_files = []

                    for fn in filenames:
                        if fn.lower().startswith(pattern) or fn.lower().endswith(
                            pattern + ".csv"
                        ):
                            dt = extract_date_from_wawibox_filename(fn)
                            if dt:
                                dated_files.append((fn, dt))

                    if dated_files:
                        latest_file = max(dated_files, key=lambda x: x[1])[0]

                        local_path = os.path.join(WAWIBOX_DOWNLOAD_PATH, latest_file)
                        ftp.download_file(latest_file, local_path)

                        WawiBoxLog.info(
                            f"Downloaded latest file {latest_file} successfully"
                        )

                is_completed = True
                TaskStatus.set_success(TaskStatus.DOWNLOAD_FILES_WAWIBOX)

    except Exception as e:
        TaskStatus.set_failure(TaskStatus.DOWNLOAD_FILES_WAWIBOX)
        WawiBoxLog.error(f"Failed to download latest Wawibox files: {e}")

    return is_completed


def parse_wawibox_file_data():
    status, errors = validate_field_maps(WAWIBOX_DATA_FIELD_MAPS)
    if errors:
        for e in errors:
            WawiBoxLog.error(e)
        return False

    # should_run = TaskStatus.should_run(TaskStatus.PARSE_DOWNLOADED_FILES_WAWIBOX)
    should_run = 1
    is_completed = False
    if status and should_run:
        is_completed = True

        file_name_patterns = tuple(p.lower() for p in WAWIBOX_DOWNLOAD_FILES_PATTERNS)

        filenames = [
            (p, f)
            for f in os.listdir(WAWIBOX_DOWNLOAD_PATH)
            if os.path.isfile(os.path.join(WAWIBOX_DOWNLOAD_PATH, f))
            for p in file_name_patterns
            if f.lower().startswith(p) or f.lower().endswith(p + ".csv")
        ]

        for pattern, filename in filenames:
            try:
                file_path = os.path.join(WAWIBOX_DOWNLOAD_PATH, filename)
                if pattern == settings.WAWIBOX_FILE_MARKETPLACE_PREFIX:
                    parse_ftp_file_to_model(
                        file_path,
                        WAWIBOX_DATA_FIELD_MAPS[pattern],
                        delimiter=",",
                        encoding="utf-8",
                        replace_all=True,
                        header_available=True,
                        use_csv=True,
                    )
                else:
                    parse_ftp_file_to_model(
                        file_path,
                        WAWIBOX_DATA_FIELD_MAPS[pattern],
                        delimiter=";",
                        encoding="utf-8",
                        replace_all=True,
                        header_available=True,
                        use_csv=True,
                    )

                WawiBoxLog.info(f"File {filename} updated on db successfully")
            except Exception as e:
                is_completed = False
                WawiBoxLog.error(f"Failed to update db from file {filename}: {e}")

        if is_completed:
            TaskStatus.set_success(TaskStatus.PARSE_DOWNLOADED_FILES_WAWIBOX)
            delete_all_files(WAWIBOX_DOWNLOAD_PATH)
        else:
            TaskStatus.set_failure(TaskStatus.PARSE_DOWNLOADED_FILES_WAWIBOX)

    return is_completed


@transaction.atomic
def _prepare_wawibox_data():
    all_ok = True

    try:
        blocked_articles = set(
            BlockedProduct.objects.values_list("article_no", flat=True)
        )
        stock_map = {s.article_no: s.inventory for s in GLSStockLevel.objects.all()}
        calculated_price = {
            s.article_no: s.calculated_sales_price for s in DynamicPrice.objects.all()
        }
        now = timezone.now()

        instances = []

        # --- GLS Master Data ---
        master_data = GLSMasterData.objects.exclude(article_no__in=blocked_articles)
        for data in master_data:
            stock = stock_map.get(data.article_no, Decimal("0"))
            availability_type_id = 1 if stock > 0 else 0
            different_delivery_time = 3 if stock > 0 else 14

            instances.append(
                WawiboxProductUpdate(
                    manufacturer_article_no=data.manufacturer_article_no,
                    manufacturer_name=data.manufacturer_name,
                    internal_number=data.article_no,
                    name=data.description,
                    is_available=availability_type_id,
                    delivery_time=different_delivery_time,
                    order_number=None,  # todo
                    price=calculated_price[data.article_no],
                    updated_at=now,
                )
            )

        # --- Additional Products ---
        additional_products = AdditionalMasterData.objects.exclude(
            article_no__in=blocked_articles
        )
        for data in additional_products:
            stock = stock_map.get(data.article_no, Decimal("0"))
            availability_type_id = 1 if stock > 0 else 2
            different_delivery_time = 3 if stock > 0 else 14

            instances.append(
                WawiboxProductUpdate(
                    manufacturer_article_no=data.manufacturer_article_no,
                    manufacturer_name=data.manufacturer_name,
                    internal_number=data.article_no,
                    name=data.description,
                    is_available=availability_type_id,
                    delivery_time=different_delivery_time,
                    order_number=None,  # todo
                    price=calculated_price[data.article_no],
                    updated_at=now,
                )
            )

        WawiboxProductUpdate.objects.all().delete()
        WawiboxProductUpdate.objects.bulk_create(instances, batch_size=500)

        WawiBoxLog.info("Data for transfer prepared successfully")
    except Exception as e:
        all_ok = False
        WawiBoxLog.error(f"Failed to prepare data for transfer: {str(e)}")

    if all_ok:
        TaskStatus.set_success(TaskStatus.PREPARE_DATA_WAWIBOX)
    else:
        TaskStatus.set_failure(TaskStatus.PREPARE_DATA_WAWIBOX)

    return all_ok


def push_wawibox_data():
    wawibox_data_prepared = _prepare_wawibox_data()
    if not wawibox_data_prepared:
        return

    csv_files_data = export_wawibox_product_data_to_csv()

    csv_path = csv_files_data["csv_path"]
    csv_name = csv_files_data["csv_name"]

    is_completed = False
    with ftps_connection(
        WAWIBOX_FTP_HOST, WAWIBOX_FTP_USER, WAWIBOX_FTP_PASSWORD, port=WAWIBOX_FTP_PORT
    ) as ftp:
        # ftp.change_dir(WAWIBOX_FTP_PATH_UPLOADS)
        try:
            ftp.upload_file(csv_path, csv_name)
            WawiBoxLog.info(f"Uploaded product data file {csv_name} successfully")
            is_completed = True
        except Exception as e:
            is_completed = False
            WawiBoxLog.error(f"Failed to upload product data file {csv_name}:  {e}")

    return is_completed


def fetch_and_save_wawibox_orders():
    return True


def wawi(request):
    # data = download_gls_files()
    # data = parse_gls_file_data()
    data = parse_wawibox_file_data()
    # data = parse_wawibox_file_data()
    # data = notify_cancelled_orders()
    # return HttpResponse(data)
    return JsonResponse(data, safe=False)
