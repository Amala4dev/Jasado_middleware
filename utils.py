import os
import stat
import csv
from datetime import datetime, date
from datetime import time as datetime_time
from datetime import timezone as datetime_timezone
from io import BytesIO, StringIO
from ftplib import FTP_TLS
from contextlib import contextmanager
import shutil
from django.core.exceptions import ImproperlyConfigured
from decimal import Decimal

import time
import hashlib, json
from django.db.models import Model
from django.db.models import BooleanField
from django.db.models import DateTimeField
from django.db.models import DecimalField
from django.db.models import CharField
import paramiko
import openpyxl
from babel.numbers import parse_decimal

from django.conf import settings
from django.apps import apps
from django.db import transaction
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.utils import timezone
from django.utils.timezone import is_aware, make_naive


ADMIN_EMAIL = settings.ADMIN_EMAIL
PENDING_DELETION_PATH = settings.PENDING_DELETION_PATH


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


def compute_hash(data: dict) -> str:
    # Convert all fields to string for stable hashing
    clean = {k: ("" if v is None else str(v)) for k, v in data.items()}
    return hashlib.sha256(json.dumps(clean, sort_keys=True).encode()).hexdigest()


def parse_ftp_file_to_model(
    file_path,
    field_map,
    delimiter="^#!",
    batch_size=800,
    encoding="cp850",
    use_hash=False,
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

            if use_hash:
                row_hash = compute_hash(data)
                data["row_hash"] = row_hash
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
            if use_hash:
                existing_objs = {
                    unique_field_value: (pk, row_hash)
                    for unique_field_value, pk, row_hash in Model.objects.filter(
                        **{f"{unique_field}__in": keys}
                    ).values_list(unique_field, "pk", "row_hash")
                }
            else:
                existing_objs = {
                    unique_field_value: (pk, "N/A")
                    for unique_field_value, pk in Model.objects.filter(
                        **{f"{unique_field}__in": keys}
                    ).values_list(unique_field, "pk")
                }

            for obj in batch:
                key = getattr(obj, unique_field)
                if key in existing_objs:
                    old_pk, old_hash = existing_objs[key]

                    obj.pk = old_pk

                    if use_hash:
                        if obj.row_hash != old_hash:
                            objs_to_update.append(obj)
                    else:
                        objs_to_update.append(obj)

                else:
                    objs_to_create.append(obj)

        else:
            objs_to_create = batch

        with transaction.atomic():
            if objs_to_update:
                update_fields = fields + (["row_hash"] if use_hash else [])
                Model.objects.bulk_update(objs_to_update, update_fields)
            if objs_to_create:
                Model.objects.bulk_create(objs_to_create)


def export_model_data(config: dict):
    file_type = config.get("file_type", "csv").lower()
    model_label = config["model_label"]
    exclude_fields = config.get("exclude_fields", ["id", "pk"])
    delimiter = config.get("delimiter", ",")
    raw_kwargs = config.get("raw_kwargs", {})

    model = apps.get_model(model_label)
    qs = model.objects.filter(**raw_kwargs)

    model_fields = [
        f
        for f in model._meta.fields
        if f.concrete and not f.many_to_many and f.name not in exclude_fields
    ]
    model_field_names = [f.name for f in model_fields]

    property_fields = [
        name
        for name, obj in model.__dict__.items()
        if isinstance(obj, property) and name not in exclude_fields
    ]

    field_names = model_field_names + property_fields

    header_labels = []

    for f in model_fields:
        header_labels.append(f.verbose_name)

    for p in property_fields:
        attr = getattr(model, p)
        if hasattr(attr.fget, "label"):
            header_labels.append(attr.fget.label)

        else:
            header_labels.append(p.replace("_", " ").title())

    if file_type == "csv":
        buffer = StringIO()
        writer = csv.writer(buffer, delimiter=delimiter)
        writer.writerow(header_labels)

        for obj in qs:
            writer.writerow([getattr(obj, f) for f in field_names])

        return buffer.getvalue().encode("utf-8")

    elif file_type == "excel":
        wb = openpyxl.Workbook()
        ws = wb.active

        ws.append(header_labels)

        for obj in qs:
            row = []
            for f in field_names:
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
    context,
    email_template="email/generic.html",
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
            cc=["johnanih237@gmail.com"],
        )
        email_msg.content_subtype = "html"
        email_msg.send(fail_silently=False)

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


def move_all_files(src_path, dst_path):
    os.makedirs(dst_path, exist_ok=True)

    for f in os.listdir(src_path):
        full_src = os.path.join(src_path, f)
        full_dst = os.path.join(dst_path, f)

        if os.path.isfile(full_src):
            if os.path.exists(full_dst):
                os.remove(full_dst)

            shutil.move(full_src, full_dst)


def delete_old_files(days, base_path=PENDING_DELETION_PATH):

    if not os.path.isdir(base_path):
        return

    cutoff = time.time() - (days * 24 * 60 * 60)

    for filename in os.listdir(base_path):
        file_path = os.path.join(base_path, filename)

        if os.path.isfile(file_path):
            if os.path.getmtime(file_path) < cutoff:
                os.remove(file_path)


def g_to_kg(value):
    return value / 1000 if value is not None else None


def mm_to_m(value):
    return value / 1000 if value is not None else None


def truncate_max_length(value, max_len):
    return value[:max_len] if value else None


def to_unix_ms(value):
    if not value:
        return None

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime.combine(value, datetime_time.min)
    else:
        raise TypeError("Expected date or datetime")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime_timezone.utc)

    return int(dt.timestamp() * 1000)


def weclapp_sales_channel():
    return {
        "SHOPWARE": "NET1",
        "AERA": "NET2",
        "WAWIBOX": "NET3",
        "DENTALHELD": "NET4",
    }


def remove_null_keys(obj):
    if isinstance(obj, dict):
        return {k: remove_null_keys(v) for k, v in obj.items() if v is not None}
    elif isinstance(obj, list):
        return [remove_null_keys(v) for v in obj if v is not None]
    else:
        return obj


def remove_empty_strings(obj):
    if isinstance(obj, dict):
        return {k: remove_empty_strings(v) for k, v in obj.items() if v != ""}
    elif isinstance(obj, list):
        return [remove_empty_strings(v) for v in obj if v != ""]
    return obj


def make_json_safe(obj):
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    if isinstance(obj, Decimal):
        return float(obj.quantize(Decimal("0.00")))
    return obj


def clean_payload(payload, json_safe=True):
    payload = remove_null_keys(payload)
    payload = remove_empty_strings(payload)
    if json_safe:
        payload = make_json_safe(payload)
    return payload


class OrderBaseModel(Model):
    order_number = CharField(max_length=100, null=True, blank=True)
    fetched_at = DateTimeField(null=True, blank=True, auto_now=True)
    weclapp_id = CharField(max_length=100, null=True, blank=True)
    synced_to_weclapp = BooleanField(default=False, db_index=True)

    class Meta:
        abstract = True

    @property
    def customer_email(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement customer_email"
        )

    def build_weclapp_order_payload(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement build_weclapp_order_payload function"
        )

    def build_weclapp_customer_payload(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement build_weclapp_customer_payload function"
        )


def normalize_text(value):
    return value.lower().strip() if value else None
