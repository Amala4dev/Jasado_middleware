import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.conf import settings
from django.urls import reverse
from django.utils.timezone import now
from utils import (
    ftp_connection,
    parse_ftp_file_to_model,
    send_email,
    validate_field_maps,
    move_all_files,
)
from .utils import (
    GlsLog,
    export_gls_orders_to_csv,
    upload_product_group_to_db,
    validate_file_and_extract_rows,
    FILE_PRODUCT_GROUP,
)
from django.http import JsonResponse, HttpResponse
from apps.core.models import TaskStatus, ExportTask
from .mapping import DATA_FIELD_MAPS
from .models import (
    GLSOrderConfirmation,
    GLSOrderStatus,
    GLSOrderHeader,
    SHIPPING_SERVICES,
)

# Constants
GLS_FTP_HOST = settings.GLS_FTP_HOST
GLS_FTP_USER = settings.GLS_FTP_USER
GLS_FTP_PASSWORD = settings.GLS_FTP_PASSWORD
GLS_FTP_PORT = settings.GLS_FTP_PORT
GLS_FTP_PATH_OUTGOING = settings.GLS_FTP_PATH_OUTGOING
GLS_FTP_PATH_INCOMING = settings.GLS_FTP_PATH_INCOMING
GLS_DOWNLOAD_PATH = settings.GLS_DOWNLOAD_PATH
PENDING_DELETION_PATH = settings.PENDING_DELETION_PATH
GLS_DOWNLOAD_FILES_EXT = settings.GLS_DOWNLOAD_FILES_EXT


def download_gls_files():
    is_completed = False
    try:
        with ftp_connection(
            GLS_FTP_HOST, GLS_FTP_USER, GLS_FTP_PASSWORD, port=GLS_FTP_PORT
        ) as ftp:
            file_attrs = [
                f
                for f in ftp.sftp.listdir_attr()
                if f.filename.endswith(tuple(GLS_DOWNLOAD_FILES_EXT))
            ]
            for f in file_attrs:
                filename = f.filename
                local_path = os.path.join(GLS_DOWNLOAD_PATH, filename)
                ftp.download_file(filename, local_path)
                # preserve GLS modified time
                os.utime(local_path, (f.st_mtime, f.st_mtime))
                GlsLog.info(f"Downloaded file {filename} successfully")

        TaskStatus.set_success(TaskStatus.DOWNLOAD_FILES_GLS)
        is_completed = True
    except Exception as e:
        TaskStatus.set_failure(TaskStatus.DOWNLOAD_FILES_GLS)
        GlsLog.error(f"Failed to download files from GLS:  {e}")

    return is_completed


def upload_gls_orders(order_header):
    csv_files = export_gls_orders_to_csv(order_header)

    header_csv_path = csv_files["header_csv_path"]
    header_csv_temp_name = csv_files["header_csv_temp_name"]
    header_csv_perm_name = csv_files["header_csv_perm_name"]

    lines_csv_path = csv_files["lines_csv_path"]
    lines_csv_temp_name = csv_files["lines_csv_temp_name"]
    lines_csv_perm_name = csv_files["lines_csv_perm_name"]

    all_ok = False
    with ftp_connection(
        GLS_FTP_HOST, GLS_FTP_USER, GLS_FTP_PASSWORD, port=GLS_FTP_PORT
    ) as ftp:
        # ftp.change_dir(GLS_FTP_PATH_INCOMING)
        all_ok = True
        try:
            if not order_header.header_uploaded:
                ftp.upload_file(header_csv_path, header_csv_temp_name)
                GlsLog.info(
                    f"Uploaded order header file {header_csv_temp_name} successfully"
                )
                order_header.header_uploaded = True
                order_header.save()
            try:
                if not order_header.header_renamed:
                    ftp.sftp.rename(header_csv_temp_name, header_csv_perm_name)
                    GlsLog.info(
                        f"Renamed order header file from {header_csv_temp_name} to {header_csv_perm_name} successfully"
                    )
                    order_header.header_renamed = True
                    order_header.save()
            except Exception as e:
                all_ok = False
                GlsLog.error(
                    f"Failed to rename order header file from {header_csv_temp_name} to {header_csv_perm_name}:  {e}"
                )
        except Exception as e:
            all_ok = False
            GlsLog.error(
                f"Failed to upload order header file {header_csv_temp_name}:  {e}"
            )

        try:
            if not order_header.lines_uploaded:
                ftp.upload_file(lines_csv_path, lines_csv_temp_name)
                GlsLog.info(
                    f"Uploaded order line file {lines_csv_temp_name} successfully"
                )
                order_header.lines_uploaded = True
                order_header.save()
            try:
                if not order_header.lines_renamed:
                    ftp.sftp.rename(lines_csv_temp_name, lines_csv_perm_name)
                    GlsLog.info(
                        f"Renamed order line file from {lines_csv_temp_name} to {lines_csv_perm_name} successfully"
                    )
                    order_header.lines_renamed = True
                    order_header.save()
            except Exception as e:
                all_ok = False
                GlsLog.error(
                    f"Failed to rename order line file from {lines_csv_temp_name} to {lines_csv_perm_name}:  {e}"
                )
        except Exception as e:
            all_ok = False
            GlsLog.error(
                f"Failed to upload order line file {lines_csv_temp_name} :  {e}"
            )

    return all_ok


def parse_gls_file_data():
    status, errors = validate_field_maps(DATA_FIELD_MAPS)
    if errors:
        for e in errors:
            GlsLog.error(e)
        return False

    all_ok = False
    if status:
        all_ok = True
        filenames = [
            f
            for f in os.listdir(GLS_DOWNLOAD_PATH)
            if os.path.isfile(os.path.join(GLS_DOWNLOAD_PATH, f))
            and f.endswith(tuple(GLS_DOWNLOAD_FILES_EXT))
        ]
        filenames = sorted(
            filenames,
            key=lambda f: os.path.getmtime(os.path.join(GLS_DOWNLOAD_PATH, f)),
        )

        for filename in filenames:
            try:
                file_path = os.path.join(GLS_DOWNLOAD_PATH, filename)
                ext = os.path.splitext(filename)[1]
                if ext in [".316", ".315"]:
                    parse_ftp_file_to_model(
                        file_path, DATA_FIELD_MAPS[ext], replace_all=True
                    )
                else:
                    parse_ftp_file_to_model(
                        file_path,
                        DATA_FIELD_MAPS[ext],
                    )

                GlsLog.info(f"File {filename} updated on db successfully")
            except Exception as e:
                all_ok = False
                GlsLog.error(f"Failed to update db from file {filename}: {e}")

        if all_ok:
            move_all_files(GLS_DOWNLOAD_PATH, PENDING_DELETION_PATH)
            TaskStatus.set_success(TaskStatus.PARSE_DOWNLOADED_FILES_GLS)
        else:
            TaskStatus.set_failure(TaskStatus.PARSE_DOWNLOADED_FILES_GLS)

    return all_ok


def push_dropshipping_orders_to_gls():
    all_ok = True
    new_order_headers = GLSOrderHeader.objects.filter(is_processed=False)
    for order_header in new_order_headers:
        is_uploaded = upload_gls_orders(order_header)
        if is_uploaded:
            new_order_headers.is_processed = True
            new_order_headers.save()
        else:
            all_ok = False

    if all_ok:
        TaskStatus.set_success(TaskStatus.UPLOAD_ORDERS_GLS)
    else:
        TaskStatus.set_failure(TaskStatus.UPLOAD_ORDERS_GLS)


def fetch_gls_order_feedback():
    new_feedbacks = GLSOrderConfirmation.objects.filter(processed=False).order_by("pk")
    if new_feedbacks.exists():
        for feedback in new_feedbacks:
            record_type = int(feedback.record_type)
            if record_type == 1:
                is_processed = handle_item_qty(feedback)
            elif record_type == 2:
                is_processed = handle_serial_number(feedback)
            elif record_type == 3:
                is_processed = handle_batch_number(feedback)
            elif record_type == 4:
                is_processed = handle_expiry_date(feedback)
            elif record_type == 5:
                is_processed = handle_siemens_no(feedback)
            elif record_type == 6:
                is_processed = handle_package_info(feedback)
            elif record_type == 7:
                is_processed = handle_planned_delivery(feedback)
            elif record_type == 8:
                is_processed = handle_backorder_info(feedback)

            feedback.processed = is_processed
            feedback.save()

        GlsLog.info(f"{new_feedbacks.count()} order feedbacks processed.")
        return True
    return False


def handle_item_qty(feedback):
    order_number = feedback.order_number
    position = feedback.position
    article_no = feedback.article_no
    delivered_qty = feedback.actual_value
    ordered_qty = feedback.ordered_qty
    control_number = feedback.control_number
    package_type = feedback.shipping_info
    delivery_date = feedback.delivery_note_date
    expected_delivery_date = feedback.expected_delivery_date
    planned_goods_receipt_date = feedback.goods_receipt_date
    status_info = feedback.info

    end_customer_id = feedback.end_customer_id
    customer_number = feedback.customer_number
    unit_price = feedback.unit_price
    internal_user = feedback.internal_user
    document_number = feedback.document_number

    if order_number and position:
        order_status, _ = GLSOrderStatus.objects.get_or_create(
            order_number=order_number, position=position
        )

    else:
        order_status, _ = GLSOrderStatus.objects.get_or_create(
            order_number=order_number,
            position=position,
            document_number=document_number,
        )

    try:
        if True:
            # if not order_status.delivered:
            is_delivery_complete = int(ordered_qty) == int(delivered_qty)

            order_status.delivered = is_delivery_complete
            order_status.delivered_qty = delivered_qty
            order_status.ordered_qty = ordered_qty
            order_status.package_type = package_type
            order_status.delivery_date = delivery_date
            order_status.article_no = article_no
            order_status.status_info = status_info
            order_status.control_number = control_number

            order_status.end_customer_id = end_customer_id
            order_status.customer_number = customer_number
            order_status.unit_price = unit_price
            order_status.internal_user = internal_user
            order_status.document_number = document_number

            if not is_delivery_complete:
                order_status.expected_delivery_date = expected_delivery_date
                order_status.planned_goods_receipt_date = planned_goods_receipt_date
            order_status.save()
        is_processed = True
    except Exception as e:
        is_processed = False
        GlsLog.error(
            f"Failed to handle record type 1 order feedback for order {order_number}, position {position}: {e}"
        )
    return is_processed


def handle_serial_number(feedback):
    order_number = feedback.order_number
    position = feedback.position
    serial_number = feedback.control_number
    document_number = feedback.document_number

    if order_number and position:
        order_status, _ = GLSOrderStatus.objects.get_or_create(
            order_number=order_number, position=position
        )

    else:
        order_status, _ = GLSOrderStatus.objects.get_or_create(
            order_number=order_number,
            position=position,
            document_number=document_number,
        )

    try:
        order_status.serial_number = serial_number
        order_status.document_number = document_number
        order_status.save()
        is_processed = True
    except Exception as e:
        is_processed = False
        GlsLog.error(
            f"Failed to handle record type 2 order feedback for order {order_number}, position {position}: {e}"
        )
    return is_processed


def handle_batch_number(feedback):
    order_number = feedback.order_number
    position = feedback.position
    batch_number = feedback.control_number
    shipping_info = feedback.shipping_info
    document_number = feedback.document_number

    if order_number and position:
        order_status, _ = GLSOrderStatus.objects.get_or_create(
            order_number=order_number, position=position
        )

    else:
        order_status, _ = GLSOrderStatus.objects.get_or_create(
            order_number=order_number,
            position=position,
            document_number=document_number,
        )
    try:
        order_status.batch_number = batch_number
        order_status.document_number = document_number
        if shipping_info:
            shipping_service = SHIPPING_SERVICES.get(shipping_info)

        order_status.shipping_service = shipping_service or shipping_info
        order_status.save()
        is_processed = True
    except Exception as e:
        is_processed = False
        GlsLog.error(
            f"Failed to handle record type 3 order feedback for order {order_number}, position {position}: {e}"
        )
    return is_processed


def handle_expiry_date(feedback):
    order_number = feedback.order_number
    position = feedback.position
    expiry_date = feedback.control_number
    document_number = feedback.document_number

    if order_number and position:
        order_status, _ = GLSOrderStatus.objects.get_or_create(
            order_number=order_number, position=position
        )

    else:
        order_status, _ = GLSOrderStatus.objects.get_or_create(
            order_number=order_number,
            position=position,
            document_number=document_number,
        )

    try:
        order_status.expiry_date = expiry_date
        order_status.document_number = document_number
        order_status.save()
        is_processed = True
    except Exception as e:
        is_processed = False
        GlsLog.error(
            f"Failed to handle record type 4 order feedback for order {order_number}, position {position}: {e}"
        )
    return is_processed


def handle_siemens_no(feedback):
    order_number = feedback.order_number
    position = feedback.position
    siemens_process_no = feedback.control_number
    document_number = feedback.document_number

    if order_number and position:
        order_status, _ = GLSOrderStatus.objects.get_or_create(
            order_number=order_number, position=position
        )

    else:
        order_status, _ = GLSOrderStatus.objects.get_or_create(
            order_number=order_number,
            position=position,
            document_number=document_number,
        )

    try:
        order_status.siemens_process_no = siemens_process_no
        order_status.document_number = document_number
        order_status.save()
        is_processed = True
    except Exception as e:
        is_processed = False
        GlsLog.error(
            f"Failed to handle record type 5 order feedback for order {order_number}, position {position}: {e}"
        )
    return is_processed


def handle_package_info(feedback):
    order_number = feedback.order_number
    position = feedback.position
    package_number = feedback.control_number
    number_of_package = feedback.ordered_qty
    shipping_info = feedback.shipping_info
    pack_time = feedback.packing_time
    pack_date = feedback.delivery_note_date
    document_number = feedback.document_number

    if order_number and position:
        order_status, _ = GLSOrderStatus.objects.get_or_create(
            order_number=order_number, position=position
        )

    else:
        order_status, _ = GLSOrderStatus.objects.get_or_create(
            order_number=order_number,
            position=position,
            document_number=document_number,
        )

    try:
        order_status.package_number = package_number
        order_status.number_of_package = number_of_package
        order_status.pack_time = pack_time
        order_status.pack_date = pack_date
        order_status.document_number = document_number

        if shipping_info:
            shipping_service = SHIPPING_SERVICES.get(shipping_info)
        order_status.shipping_service = shipping_service or shipping_info
        order_status.save()
        is_processed = True
    except Exception as e:
        is_processed = False
        GlsLog.error(
            f"Failed to handle record type 6 order feedback for order {order_number}, position {position}: {e}"
        )
    return is_processed


def handle_planned_delivery(feedback):
    order_number = feedback.order_number
    position = feedback.position
    planned_qty = feedback.actual_value
    dfu_number = feedback.control_number
    planned_goods_receipt_date = feedback.goods_receipt_date
    expected_delivery_date = feedback.expected_delivery_date
    status_info = feedback.info
    end_customer_id = feedback.end_customer_id
    customer_number = feedback.customer_number
    unit_price = feedback.unit_price
    internal_user = feedback.internal_user
    article_no = feedback.article_no

    try:
        if order_number and position:
            order_status, _ = GLSOrderStatus.objects.get_or_create(
                order_number=order_number, position=position
            )

        else:
            order_status, _ = GLSOrderStatus.objects.get_or_create(
                order_number=order_number,
                position=position,
                dfu_number=dfu_number,
            )

        order_status.dfu_number = dfu_number
        order_status.status_info = status_info
        order_status.expected_delivery_date = expected_delivery_date
        order_status.planned_qty = planned_qty
        order_status.end_customer_id = end_customer_id
        order_status.customer_number = customer_number
        order_status.unit_price = unit_price
        order_status.internal_user = internal_user
        order_status.article_no = article_no
        order_status.planned_goods_receipt_date = planned_goods_receipt_date
        order_status.save()

        is_processed = True

    except Exception as e:
        is_processed = False
        GlsLog.error(
            f"Failed to handle record type 7 order feedback for order {order_number}, position {position}: {e}"
        )

    return is_processed


def handle_backorder_info(feedback):
    order_number = feedback.order_number
    document_number = feedback.document_number
    end_customer_id = feedback.end_customer_id
    backorder_text = feedback.backorder_text

    try:
        if order_number:
            updated = GLSOrderStatus.objects.filter(order_number=order_number).update(
                backorder_text=backorder_text,
            )
            if updated == 0:
                GLSOrderStatus.objects.create(
                    order_number=order_number,
                    backorder_text=backorder_text,
                    delivered=False,
                    document_number=document_number,
                    end_customer_id=end_customer_id,
                )
            is_processed = True
        else:
            is_processed = False
    except Exception as e:
        is_processed = False
        GlsLog.error(
            f"Failed to handle record type 8 order feedback for order {order_number}: {e}"
        )
    return is_processed


def notify_cancelled_orders():
    cancelled_orders = GLSOrderStatus.objects.cancelled()
    if cancelled_orders.exists():
        subject = f"Failed Delivery Report - {now().date()}"
        template = "email/cancelled_delivery.html"
        context = {
            "orders": cancelled_orders,
        }
        response = send_email(subject, template, context)

        if response["sent"]:
            cancelled_orders.update(admin_notified=True)
        else:
            GlsLog.error(
                f"Failed to send email for cancelled deliveries: {response.get('error')}"
            )


@staff_member_required
@require_POST
def export_master_data(request):
    file_type = request.POST.get("file_type") or "excel"
    changelist_url = reverse("admin:gls_glsmasterdata_changelist")

    if file_type not in ["csv", "excel"]:
        messages.error(request, "Please choose a valid file type.")
        return redirect(changelist_url)

    config = {
        "file_type": file_type,
        "model_label": "gls.GLSMasterData",
        "display_name": "GLS Master Data",
        "exclude_fields": ["id", "manufacturer", "pk", "updated_at"],
    }

    ExportTask.objects.create(
        user=request.user,
        name=config["display_name"],
        file_type=file_type,
        config=config,
    )

    messages.success(
        request,
        "Export task has been created. You will receive an email once it is ready for download.",
    )
    return redirect(changelist_url)


@staff_member_required
@require_POST
def upload_product_group(request):
    uploaded_file = request.FILES.get("file")
    changelist_url = reverse("admin:gls_glsproductgroup_changelist")

    if not uploaded_file:
        messages.error(request, "Please choose a .xlsx file.")
        return redirect(changelist_url)

    try:
        rows = validate_file_and_extract_rows(uploaded_file, FILE_PRODUCT_GROUP)
        upload_status = upload_product_group_to_db(rows)
    except ValueError as err:
        messages.error(request, str(err))
        return redirect(changelist_url)
    except Exception as err:
        messages.error(request, f"Import failed: {err}")
        return redirect(changelist_url)

    filename = getattr(uploaded_file, "name", "")
    messages.success(
        request, f"Imported {upload_status.get('total', 0)} rows from “{filename}”."
    )
    return redirect(changelist_url)


def index(request):
    # data = download_gls_files()
    data = parse_gls_file_data()
    # data = notify_cancelled_orders()
    # data = notify_cancelled_orders()
    # return HttpResponse(data)
    return JsonResponse(data, safe=False)
