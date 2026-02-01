from apps.core.models import LogEntry
from .mapping import field_map_update_csv
import os
import csv
from django.conf import settings


class DentalheldLog:
    @staticmethod
    def info(msg):
        LogEntry.objects.create(
            source=LogEntry.DENTALHELD, level=LogEntry.INFO, message=msg
        )

    @staticmethod
    def warning(msg):
        LogEntry.objects.create(
            source=LogEntry.DENTALHELD, level=LogEntry.WARNING, message=msg
        )

    @staticmethod
    def error(msg):
        LogEntry.objects.create(
            source=LogEntry.DENTALHELD, level=LogEntry.ERROR, message=msg
        )


def export_dentalheld_products_to_csv(export_products):
    model_fields = [m for m, _ in field_map_update_csv]
    headers = [c for _, c in field_map_update_csv]
    file_name = settings.DENTALHELD_FILE_UPDATE_CSV
    DENTALHELD_UPLOAD_PATH = settings.DENTALHELD_UPLOAD_PATH

    os.makedirs(DENTALHELD_UPLOAD_PATH, exist_ok=True)

    csv_file_path = os.path.join(DENTALHELD_UPLOAD_PATH, file_name)

    with open(csv_file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(
            f,
            delimiter=";",
            quotechar='"',
            quoting=csv.QUOTE_ALL,
        )

        writer.writerow(headers)

        for obj in export_products:
            writer.writerow(
                [
                    getattr(obj, field) if getattr(obj, field) is not None else ""
                    for field in model_fields
                ]
            )

    return csv_file_path
