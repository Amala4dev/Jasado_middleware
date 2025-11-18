from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.db import models
from django.db.models import F
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.db.models import Model
from django.db.models import QuerySet
from django.db.models import ForeignKey
from django.db.models import OneToOneField
from django.db.models import CharField
from django.db.models import BooleanField
from django.db.models import DateField
from django.db.models import JSONField
from django.db.models import IntegerField
from django.db.models import DateTimeField
from django.db.models import TextField
from django.db.models import DecimalField
from utils import CleanDecimalField
from django.db.models import SET_NULL
from django.contrib.auth import get_user_model

User = get_user_model()


class LogEntry(models.Model):
    # Levels
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

    # Sources
    AERA = "AERA"
    GLS = "GLS"
    WECLAPP = "WECLAPP"
    SHOPWARE = "SHOPWARE"
    WAWIBOX = "WAWIBOX"
    DENTALHELD = "DENTALHELD"
    SYSTEM = "SYSTEM"

    source = models.CharField(max_length=50)
    level = models.CharField(max_length=20)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Automation Log"
        verbose_name_plural = "Automation Logs"

    def __str__(self):
        return f"[{self.source}] {self.level} - {self.message[:50]}"


class TaskStatus(models.Model):
    DOWNLOAD_FILES_GLS = "download_files_gls"
    DOWNLOAD_FILES_WAWIBOX = "download_files_wawibox"
    UPLOAD_ORDERS_GLS = "upload_orders_gls"
    PARSE_DOWNLOADED_FILES_GLS = "parse_gls_file_data"
    PARSE_DOWNLOADED_FILES_WAWIBOX = "parse_wawibox_file_data"
    FETCH_PRICES_AERA = "fetch_prices_aera"
    FETCH_PRICES_WAWIBOX = "fetch_prices_wawibox"
    PREPARE_DATA_AERA = "prepare_data_aera"
    PREPARE_DATA_WAWIBOX = "prepare_data_wawibox"
    DATA_TRANSFER_AERA = "data_transfer_aera"
    UPDATE_PRICES_AERA = "update_prices_aera"
    FETCH_ORDERS_AERA = "fetch_orders_aera"

    name = models.CharField(max_length=100, unique=True)
    status = models.BooleanField(default=False)
    last_run = models.DateTimeField(auto_now=True)

    @classmethod
    def should_run(cls, task_name):
        task = cls.objects.filter(name=task_name).first()
        if not task:
            return True
        now = timezone.now()
        if not task.status:
            return (now - task.last_run) >= timedelta(hours=4)
        return task.last_run.date() != now.date()

    @classmethod
    def set_success(cls, task_name):
        cls.objects.update_or_create(
            name=task_name,
            defaults={"status": True, "last_run": timezone.now()},
        )

    @classmethod
    def set_failure(cls, task_name):
        cls.objects.update_or_create(
            name=task_name,
            defaults={"status": False, "last_run": timezone.now()},
        )


class Product(Model):
    manufacturer_article_no = CharField(
        max_length=50,
        db_index=True,
        null=True,
        blank=True,
    )
    supplier_article_no = CharField(
        max_length=100,
        db_index=True,
        null=True,
        blank=True,
    )
    supplier = CharField(max_length=255, default="GLS")
    sku = CharField(max_length=50, null=True, blank=True, unique=True, db_index=True)
    name = CharField(max_length=255, null=True, blank=True)
    manufacturer = CharField(max_length=255, editable=False, null=True, blank=True)
    manufacturer_id = CharField(max_length=255, editable=False, null=True, blank=True)
    description = TextField(null=True, blank=True)
    created_at = DateTimeField(editable=False, auto_now_add=True)
    updated_at = DateTimeField(editable=False, auto_now=True)
    is_blocked = BooleanField(default=True)

    class Meta:
        unique_together = ("supplier", "supplier_article_no")
        verbose_name_plural = "All Products"

    def __str__(self):
        return self.sku or "product"

    def generate_sku(self):
        if not self.supplier_article_no:
            return None

        if self.supplier == "GLS":
            return f"LG{self.supplier_article_no}"

        prefix = (self.manufacturer or "")[:2].upper()
        return f"{prefix}{self.supplier_article_no}"

    @property
    def manufacturer_name(self):
        from apps.gls.models import GLSSupplier

        # If NON-GLS already has a name, use it
        if self.manufacturer and not self.manufacturer_id:
            return self.manufacturer

        # GLS case: manufacturer_id → lookup name
        if self.manufacturer_id:
            s = GLSSupplier.objects.filter(supplier_no=self.manufacturer_id).first()
            if s:
                return f"{s.name1 or ''} {s.name2 or ''}".strip() or "Unknown"

        return "Unknown"


class AdditionalMasterData(Model):
    product = ForeignKey(
        Product,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="additional_master_data",
        editable=False,
    )
    name = CharField(max_length=250, blank=True, null=True)
    article_no = CharField(max_length=50, blank=True, null=True)
    description = CharField(max_length=255, blank=True, null=True)
    active = BooleanField(default=True)
    width = CleanDecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    height = CleanDecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    length = CleanDecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    weight = CleanDecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    manufacturer_article_no = CharField(max_length=50, blank=True, null=True)
    article_calculation_price = CleanDecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="purchase price already including handling fee",
    )
    batch_number_required = BooleanField(default=True)
    gtin = CharField(max_length=100, blank=True, null=True)
    manufacturer = CharField(max_length=200, blank=True, null=True)
    stock = CleanDecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    store_refrigerated = BooleanField(default=False)
    created_at = models.DateTimeField(editable=False, auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("manufacturer_article_no", "manufacturer"),)
        verbose_name = "Non-GLS Product"
        verbose_name_plural = "Non-GLS Products"

    def __str__(self):
        return self.article_no or "additional product"


class BlockedProduct(Model):
    product = ForeignKey(
        Product,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="blocked_item",
        editable=False,
    )
    name = CharField(max_length=250, blank=True, null=True)
    article_no = CharField(max_length=50, unique=True)
    manufacturer_article_no = CharField(max_length=50, blank=True, null=True)
    manufacturer = CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(editable=False, auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    def __str__(self):
        return self.article_no


class DynamicPrice(models.Model):
    product = ForeignKey(
        Product,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="dynamic_price",
        editable=False,
    )
    sku = models.CharField(max_length=50, unique=True)
    net_own = models.DecimalField(
        verbose_name="AERA Own Net Price",
        help_text="Net price from AERA for Jasado’s own offer",
        max_digits=12,
        decimal_places=2,
    )
    net_top_1 = models.DecimalField(
        verbose_name="AERA Top 1 Net Price",
        help_text="Lowest competitor net price on AERA",
        max_digits=12,
        decimal_places=2,
    )
    net_top_2 = models.DecimalField(
        verbose_name="AERA Top 2 Net Price",
        help_text="Second lowest competitor net price on AERA",
        max_digits=12,
        decimal_places=2,
    )
    net_top_3 = models.DecimalField(
        verbose_name="AERA Top 3 Net Price",
        help_text="Third lowest competitor net price on AERA",
        max_digits=12,
        decimal_places=2,
    )
    calculated_sales_price = models.DecimalField(
        verbose_name="Calculated Price",
        help_text="Final sales price calculated by middleware",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    last_calculated = models.DateTimeField(
        verbose_name="Last Calculated",
        help_text="Timestamp of the last price calculation",
        null=True,
        blank=True,
    )
    last_fetch_from_aera = models.DateTimeField(
        verbose_name="Last Fetched from AERA",
        help_text="Timestamp of the last data fetch from AERA",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.sku


class ExportTask(Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"

    FILE_TYPES = [
        ("csv", "CSV"),
        ("excel", "Excel"),
    ]
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_DONE, "Done"),
        (STATUS_FAILED, "Failed"),
    ]

    user = ForeignKey(User, on_delete=SET_NULL, null=True, blank=True, editable=False)
    name = CharField(max_length=100, default="file")
    file_type = CharField(max_length=10, choices=FILE_TYPES, default="csv")
    config = JSONField(default=dict, editable=False)
    download_url = CharField(max_length=500, blank=True, null=True)
    status = CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = TextField(blank=True, null=True)
    created_at = DateTimeField(auto_now_add=True)
    completed_at = DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.name
