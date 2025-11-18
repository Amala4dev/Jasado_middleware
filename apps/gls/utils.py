from apps.core.models import LogEntry
import os
import re
from apps.gls.mapping import field_map_101
from apps.gls.mapping import field_map_102
from django.conf import settings

GLS_UPLOAD_PATH = settings.GLS_UPLOAD_PATH


class GlsLog:
    @staticmethod
    def info(msg):
        LogEntry.objects.create(source=LogEntry.GLS, level=LogEntry.INFO, message=msg)

    @staticmethod
    def warning(msg):
        LogEntry.objects.create(
            source=LogEntry.GLS, level=LogEntry.WARNING, message=msg
        )

    @staticmethod
    def error(msg):
        LogEntry.objects.create(source=LogEntry.GLS, level=LogEntry.ERROR, message=msg)


def export_gls_orders_to_csv(order_header, delimiter="^#!"):
    header_rows = []
    order_lines = []

    header_fields = field_map_101["fields"]
    header_values = [
        _format_gls_value(getattr(order_header, field_name), field_type)
        for field_name, field_type in header_fields
    ]
    header_rows.append(delimiter.join(map(str, header_values)))

    line_fields = field_map_102["fields"]
    for line in order_header.lines.all():
        line_values = [
            _format_gls_value(getattr(line, field_name), field_type)
            for field_name, field_type in line_fields
        ]
        order_lines.append(delimiter.join(map(str, line_values)))

    os.makedirs(GLS_UPLOAD_PATH, exist_ok=True)
    header_csv_temp_name = f"{order_header.order_no}.101.tmp"
    header_csv_perm_name = f"{order_header.order_no}.101"

    lines_csv_temp_name = f"{order_header.order_no}.102.tmp"
    lines_csv_perm_name = f"{order_header.order_no}.102"

    header_csv_path = os.path.join(GLS_UPLOAD_PATH, header_csv_perm_name)
    lines_csv_path = os.path.join(GLS_UPLOAD_PATH, lines_csv_perm_name)

    header_data = "\r\n".join(header_rows)
    lines_data = "\r\n".join(order_lines)

    with open(header_csv_path, "w", encoding="cp850") as f:
        f.write(header_data)
    with open(lines_csv_path, "w", encoding="cp850") as f:
        f.write(lines_data)

    return {
        "header_csv_path": header_csv_path,
        "header_csv_temp_name": header_csv_temp_name,
        "header_csv_perm_name": header_csv_perm_name,
        "lines_csv_path": lines_csv_path,
        "lines_csv_temp_name": lines_csv_temp_name,
        "lines_csv_perm_name": lines_csv_perm_name,
    }


def _format_gls_value(value, field_type):
    if value in (None, ""):
        return ""

    match = re.match(r"(\d+)?([a-zA-Z,/_]+)", field_type)
    length = int(match.group(1)) if match.group(1) else None
    ftype = match.group(2)

    if ftype.endswith("c"):
        value = str(value).strip().upper()
    elif ftype.endswith("t"):
        value = str(value).strip()
    elif ftype == "d":
        value = str(int(float(value))).replace(".", "").replace(",", "")
    elif ftype == "d,":
        value = str(value).replace(",", "").replace(".", ",")
    elif ftype.startswith("TT"):
        value = value.strftime("%d.%m.%y") if value else ""
    elif ftype in ("J/N", "c_bool"):
        value = "J" if value else "N"
    else:
        value = str(value)

    if length and not ftype.startswith("TT"):
        value = value[:length]

    return value
