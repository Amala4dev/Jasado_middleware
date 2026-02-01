import os
from django.conf import settings
from django.utils import timezone

from utils import (
    ftps_connection,
    parse_ftp_file_to_model,
    validate_field_maps,
    move_all_files,
)
from .utils import (
    WawiBoxLog,
    export_wawibox_product_data_to_csv,
    extract_date_from_wawibox_filename,
)
from django.http import JsonResponse
from .mapping import WAWIBOX_DATA_FIELD_MAPS
from .models import WawiboxExport

# Constants
WAWIBOX_FTP_HOST = settings.WAWIBOX_FTP_HOST
WAWIBOX_FTP_USER = settings.WAWIBOX_FTP_USER
WAWIBOX_FTP_PASSWORD = settings.WAWIBOX_FTP_PASSWORD
WAWIBOX_FTP_PORT = settings.WAWIBOX_FTP_PORT
WAWIBOX_FTP_PATH_DOWNLOADS = settings.WAWIBOX_FTP_PATH_DOWNLOADS
WAWIBOX_FTP_PATH_UPLOADS = settings.WAWIBOX_FTP_PATH_UPLOADS
WAWIBOX_DOWNLOAD_PATH = settings.WAWIBOX_DOWNLOAD_PATH
WAWIBOX_DOWNLOAD_FILES_PATTERNS = settings.WAWIBOX_DOWNLOAD_FILES_PATTERNS
PENDING_DELETION_PATH = settings.PENDING_DELETION_PATH


def download_wawibox_files():
    is_completed = False

    try:
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

    except Exception as e:
        WawiBoxLog.error(f"Failed to download latest Wawibox files: {e}")

    return is_completed


def parse_wawibox_file_data():
    status, errors = validate_field_maps(WAWIBOX_DATA_FIELD_MAPS)
    if errors:
        for e in errors:
            WawiBoxLog.error(e)
        return False

    is_completed = False
    if status:
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
            move_all_files(WAWIBOX_DOWNLOAD_PATH, PENDING_DELETION_PATH)
    return is_completed


def push_products_to_wawibox():

    csv_files_data = export_wawibox_product_data_to_csv()

    csv_path = csv_files_data["csv_path"]
    csv_name = csv_files_data["csv_name"]

    is_completed = False
    with ftps_connection(
        WAWIBOX_FTP_HOST, WAWIBOX_FTP_USER, WAWIBOX_FTP_PASSWORD, port=WAWIBOX_FTP_PORT
    ) as ftp:
        # ftp.change_dir(WAWIBOX_FTP_PATH_UPLOADS)
        try:
            # ftp.upload_file(csv_path, csv_name)
            # WawiBoxLog.info(f"Uploaded product export file {csv_name} successfully")
            # WawiboxExport.objects.all().update(last_pushed_to_wawibox=timezone.now())
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
