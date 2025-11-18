import paramiko
import stat
import csv
from contextlib import contextmanager
from django.apps import apps
from django.utils import timezone
from datetime import datetime
from django.db.models import DecimalField
from decimal import Decimal
from django.db import transaction
from babel.numbers import parse_decimal
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
import csv
from django.db.models import Model
from io import BytesIO
from io import StringIO
import os
from ftplib import FTP_TLS
import stat
from django.utils.timezone import is_aware, make_naive
import re
from apps.gls.mapping import field_map_101
from apps.gls.mapping import field_map_102
from django.conf import settings
from django.apps import apps
from django.http import HttpResponse
import openpyxl
from django.db.models import ForeignKey

GLS_UPLOAD_PATH = settings.GLS_UPLOAD_PATH
ADMIN_EMAIL = settings.ADMIN_EMAIL


class CleanDecimalField(DecimalField):
    def to_python(self, value):
        if isinstance(value, str):
            value = parse_decimal(value, locale="de")
        return super().to_python(value)


class FTPClient:
    def __init__(self, host, user, password, port=22, timeout=30):
        self.host = host
        self.user = user
        self.password = password
        self.port = int(port)
        self.timeout = timeout
        self.transport = None
        self.sftp = None

    def connect(self):
        self.transport = paramiko.Transport((self.host, self.port))
        self.transport.connect(username=self.user, password=self.password)
        self.sftp = paramiko.SFTPClient.from_transport(self.transport)
        return self

    def list_files(self, path="."):
        return self.sftp.listdir(path)

    def download_file(self, remote_path, local_path):
        self.sftp.get(remote_path, local_path)

    def upload_file(self, local_path, remote_path):
        self.sftp.put(local_path, remote_path)

    def change_dir(self, path):
        self.sftp.chdir(path)

    def list_dir(self):
        for f in self.sftp.listdir_attr():
            print(f.filename, "DIR" if stat.S_ISDIR(f.st_mode) else "FILE")

    def disconnect(self):
        if self.sftp:
            self.sftp.close()
        if self.transport:
            self.transport.close()


class FTPSClient:
    def __init__(self, host, user, password, port=21, timeout=30):
        self.host = host
        self.user = user
        self.password = password
        self.port = int(port)
        self.timeout = timeout
        self.ftps = None

    def connect(self):
        self.ftps = FTP_TLS(timeout=self.timeout)
        self.ftps.connect(self.host, self.port)
        self.ftps.auth()  # secure control connection
        self.ftps.prot_p()  # secure data connection
        self.ftps.login(self.user, self.password)
        return self

    def list_files(self, path="."):
        return self.ftps.nlst(path)

    def download_file(self, remote_path, local_path):
        with open(local_path, "wb") as f:
            self.ftps.retrbinary(f"RETR {remote_path}", f.write)

    def upload_file(self, local_path, remote_path):
        with open(local_path, "rb") as f:
            self.ftps.storbinary(f"STOR {remote_path}", f)

    def change_dir(self, path):
        self.ftps.cwd(path)

    def list_dir(self):
        lines = []
        self.ftps.retrlines("LIST", lines.append)
        for line in lines:
            print(line)

    def disconnect(self):
        try:
            if self.ftps:
                self.ftps.quit()
        except:
            pass


@contextmanager
def ftp_connection(host, user, password, port=22, timeout=30):
    client = FTPClient(host, user, password, port, timeout).connect()
    try:
        yield client
    finally:
        client.disconnect()


@contextmanager
def ftps_connection(host, user, password, port=21, timeout=30):
    client = FTPSClient(host, user, password, port, timeout).connect()
    try:
        yield client
    finally:
        client.disconnect()


def make_time_zone_aware(dt_str):
    if not dt_str:
        return None
    dt = datetime.fromisoformat(dt_str)
    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt


def parse_ftp_file_to_model(
    file_path,
    field_map,
    delimiter="^#!",
    batch_size=1500,
    encoding="cp850",
    replace_all=False,
    header_available=False,
    use_csv=False,
):
    model_label = field_map["model_label"]
    fields = field_map["fields"]
    unique_field = field_map["unique_field"]
    boolean_fields = field_map["boolean_fields"]
    date_fields = field_map["date_fields"]
    code_fields = field_map.get("code_fields", [])
    Model = apps.get_model(model_label)

    objects = []

    with open(file_path, "r", encoding=encoding) as f:
        if header_available:
            next(f)
        for line in f:
            line = line.strip()
            if not line:
                continue
            if use_csv:
                values = next(csv.reader([line], delimiter=delimiter))
            else:
                values = line.split(delimiter)
            data = {}

            for i, field_name in enumerate(fields):
                if i >= len(values):
                    continue

                value = values[i].strip()

                if field_name in boolean_fields:
                    value = str(value) in ["j", "J", "y", "Y", "1", "true", "TRUE"]

                elif field_name in date_fields:
                    if value:
                        date_parsed = False
                        for fmt in ("%d.%m.%y", "%d.%m.%Y"):
                            try:
                                value = datetime.strptime(value, fmt)
                                date_parsed = True
                                break
                            except ValueError:
                                continue
                        if not date_parsed:
                            raise ValueError(
                                f"Invalid date format for field '{field_name}': {value}"
                            )
                    else:
                        value = None

                elif field_name in code_fields:
                    value = value.upper()

                if value == "":
                    value = None
                data[field_name] = value

            if data:
                objects.append(Model(**data))

    if replace_all:
        Model.objects.all().delete()
        Model.objects.bulk_create(objects, batch_size=batch_size)
        return

    for i in range(0, len(objects), batch_size):
        batch = objects[i : i + batch_size]
        objs_to_update = []
        objs_to_create = []
        if unique_field:
            keys = [getattr(obj, unique_field) for obj in batch]
            existing_objs = {
                unique_field_value: pk
                for unique_field_value, pk in Model.objects.filter(
                    **{f"{unique_field}__in": keys}
                ).values_list(unique_field, "pk")
            }

            for obj in batch:
                key = getattr(obj, unique_field)
                if key in existing_objs:
                    existing_obj_pk = existing_objs[key]
                    obj.pk = existing_obj_pk
                    objs_to_update.append(obj)
                else:
                    objs_to_create.append(obj)

        else:
            objs_to_create = batch

        with transaction.atomic():
            if objs_to_update:
                Model.objects.bulk_update(objs_to_update, fields)
            if objs_to_create:
                Model.objects.bulk_create(objs_to_create)


def export_model_data(config: dict):
    """
    Export Django model data to CSV or Excel and trigger download.

    config = {
        "file_type": "csv" or "excel",
        "model_label": "app_label.ModelName",
        "display_name": "GLS Master Data",
        "exclude_fields": ["id", "created_at"],
        "delimiter": ",",  # for CSV
        "raw_kwargs": {"id__in": [1, 2, 3]},
    }
    """
    file_type = config.get("file_type", "csv").lower()
    model_label = config["model_label"]
    exclude_fields = config.get("exclude_fields", ["id", "pk"])
    delimiter = config.get("delimiter", ",")
    raw_kwargs = config.get("raw_kwargs", {})

    model = apps.get_model(model_label)
    qs = model.objects.filter(**raw_kwargs)

    fields = [
        f.name
        for f in model._meta.get_fields()
        if f.concrete and not f.many_to_many and f.name not in exclude_fields
    ]
    fields += [p for p in dir(model) if isinstance(getattr(model, p), property)]

    if file_type == "csv":
        buffer = StringIO()
        writer = csv.writer(buffer, delimiter=delimiter)
        writer.writerow(fields)
        for obj in qs:
            writer.writerow([getattr(obj, f) for f in fields])
        return buffer.getvalue().encode("utf-8")

    elif file_type == "excel":
        wb = openpyxl.Workbook()
        ws = wb.active
        header = [
            f.verbose_name.title()
            for f in model._meta.fields
            if f.name not in exclude_fields
        ]
        ws.append(header)

        for obj in qs:
            row = []
            for f in fields:
                value = getattr(obj, f)
                if isinstance(value, datetime) and is_aware(value):
                    value = make_naive(value)
                if isinstance(value, Model):
                    value = str(value)
                row.append(value)
            ws.append(row)
        output = BytesIO()
        wb.save(output)
        return output.getvalue()

    else:
        raise ValueError("Invalid file_type. Must be 'csv' or 'excel'.")


def send_email(
    subject,
    email_template,
    context,
    from_email=None,
    recipient_email=ADMIN_EMAIL,
):
    try:
        message = render_to_string(email_template, context)
        email_msg = EmailMessage(
            subject=subject,
            body=message,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email],
        )
        email_msg.content_subtype = "html"
        email_msg.send()

        response = {"sent": True}
    except Exception as e:
        response = {"sent": False, "error": str(e)}

    return response


def validate_field_maps(field_map_dict):
    errors = []
    for key, fmap in field_map_dict.items():
        model_label = fmap.get("model_label")
        if not model_label:
            continue
        app_label, model_name = model_label.split(".")
        model = apps.get_model(app_label, model_name)

        model_fields = {f.name for f in model._meta.get_fields()}

        field_names = [
            f[0] if isinstance(f, (list, tuple)) else f for f in fmap.get("fields", [])
        ]

        missing = [f for f in field_names if f not in model_fields]
        if missing:
            errors.append(
                f"{model_label} missing fields on field mapping: {', '.join(missing)}"
            )

    if errors:
        return False, errors
    return True, errors


def delete_all_files(path):
    for f in os.listdir(path):
        full = os.path.join(path, f)
        if os.path.isfile(full):
            os.remove(full)
