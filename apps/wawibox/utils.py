from apps.core.models import LogEntry
from apps.core.models import LogEntry
import os
import re
from apps.wawibox.mapping import field_map_wawibox_file_upload
from django.conf import settings
from .models import WawiboxExport
import re
import datetime

WAWIBOX_UPLOAD_PATH = settings.WAWIBOX_UPLOAD_PATH


class WawiBoxLog:
    @staticmethod
    def info(msg):
        LogEntry.objects.create(
            source=LogEntry.WAWIBOX, level=LogEntry.INFO, message=msg
        )

    @staticmethod
    def warning(msg):
        LogEntry.objects.create(
            source=LogEntry.WAWIBOX, level=LogEntry.WARNING, message=msg
        )

    @staticmethod
    def error(msg):
        LogEntry.objects.create(
            source=LogEntry.WAWIBOX, level=LogEntry.ERROR, message=msg
        )


def export_wawibox_product_data_to_csv(delimiter=";"):
    product_list = []

    product_data_fields = field_map_wawibox_file_upload["fields"]
    for product_data in WawiboxExport.objects.iterator():
        product_instance_values = [
            _format_wawibox_value(getattr(product_data, field_name), field_type)
            for field_name, field_type in product_data_fields
        ]
        product_list.append(delimiter.join(map(str, product_instance_values)))

    os.makedirs(WAWIBOX_UPLOAD_PATH, exist_ok=True)

    csv_name = "wawibox_product_export.csv"
    csv_path = os.path.join(WAWIBOX_UPLOAD_PATH, csv_name)

    final_product_data = "\r\n".join(product_list)

    with open(csv_path, "w", encoding="cp850") as f:
        f.write(final_product_data)

    return {
        "csv_path": csv_path,
        "csv_name": csv_name,
    }


def _format_wawibox_value(value, ftype):
    if value in (None, ""):
        return ""

    if ftype == "str":
        return str(value).strip()

    if ftype == "bool_01":
        return "1" if value else "0"

    if ftype == "int":
        return str(int(value))

    if ftype == "int_012":
        v = int(value)
        if v not in (0, 1, 2):
            raise ValueError("MwSt must be 0, 1, or 2")
        return str(v)

    if ftype == "decimal":
        return f"{float(value):.2f}"

    if ftype == "date_iso":
        return value.strftime("%Y-%m-%d")

    return str(value)


def extract_date_from_wawibox_filename(filename):
    """
    Extract date from:
    - DD.MM.YYYY (e.g. 30.07.2025)
    - jasado-DD.MM.YYYY-price_comparison.csv
    - marketplaceDDMMYYYY.csv
    """

    # 1. Try DD.MM.YYYY (jasado or standalone)
    match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", filename)
    if match:
        dd, mm, yyyy = match.groups()
        return datetime.date(int(yyyy), int(mm), int(dd))

    # 2. Try marketplaceDDMMYYYY.csv
    match = re.search(r"marketplace(\d{2})(\d{2})(\d{4})", filename)
    if match:
        dd, mm, yyyy = match.groups()
        return datetime.date(int(yyyy), int(mm), int(dd))

    return None
