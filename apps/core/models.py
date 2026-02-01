from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.db import models
from django.db.models import Model
from django.db.models import ForeignKey
from django.db.models import CharField
from django.db.models import DateField
from django.db.models import BooleanField
from django.db.models import IntegerField
from django.db.models import JSONField
from django.db.models import DateTimeField
from django.db.models import TextField
from django.db.models import DecimalField
from utils import CleanDecimalField
from django.db.models import SET_NULL
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


class LogEntry(models.Model):
    # Levels
    INFO = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"

    # Sources
    AERA = "AERA"
    GLS = "GLS"
    WECLAPP = "WECLAPP"
    SHOPWARE = "SHOPWARE"
    WAWIBOX = "WAWIBOX"
    DENTALHELD = "DENTALHELD"
    CORE = "CORE"

    source = models.CharField(max_length=50)
    level = models.CharField(max_length=20)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Automation Log"
        verbose_name_plural = "Automation Logs"

    def __str__(self):
        return f"[{self.source}] {self.level} - {self.message[:50]}"

    def save(self, *args, **kwargs):
        is_error = self.level == self.ERROR
        super().save(*args, **kwargs)
        if is_error:
            from utils import send_email

            subject = "Error in Automation"

            context = {
                "message": self.message,
            }
            send_email(subject, context)


class Product(Model):
    SUPPLIER_GLS = "GLS"
    SUPPLIER_NON_GLS = "NON-GLS"

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
    supplier = CharField(max_length=255, default=SUPPLIER_GLS)
    sku = CharField(max_length=50, null=True, blank=True, unique=True, db_index=True)
    weclapp_id = CharField(
        max_length=100, null=True, blank=True, unique=True, db_index=True
    )
    weclapp_article_supply_source_id = CharField(
        max_length=100, null=True, blank=True, db_index=True
    )
    name = CharField(max_length=255, null=True, blank=True)
    manufacturer = CharField(max_length=255, editable=False, null=True, blank=True)
    manufacturer_id = CharField(max_length=255, editable=False, null=True, blank=True)
    gls_article_group_no = CharField(max_length=50, blank=True, null=True)
    description = TextField(null=True, blank=True)
    aera_sales_price = DecimalField(
        max_digits=12,
        help_text="Last calculated Aera sales price",
        default=0.0,
        decimal_places=2,
    )
    wawibox_sales_price = DecimalField(
        max_digits=12,
        help_text="Last calculated Wawibox sales price",
        default=0.0,
        decimal_places=2,
    )
    aera_gift_sales_price = DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Aera Sales price when gift promotion applies",
    )
    wawibox_gift_sales_price = DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Wawibox Sales price when gift promotion applies",
    )

    gift_min_qty = IntegerField(
        null=True,
        blank=True,
        help_text="Minimum quantity for gift price",
    )

    gift_paid_qty = IntegerField(null=True, blank=True)
    gift_free_qty = IntegerField(null=True, blank=True)
    gift_valid_from = DateField(blank=True, null=True)
    gift_valid_until = DateField(blank=True, null=True)
    gift_promo_code = CharField(max_length=50, null=True, blank=True)
    gift_action_type = CharField(max_length=50, null=True, blank=True)
    has_gift_price = BooleanField(default=False)

    store_refrigerated = BooleanField(default=False)
    created_at = DateTimeField(editable=False, auto_now_add=True)
    updated_at = DateTimeField(editable=False, auto_now=True)
    is_blocked = BooleanField(default=False)

    class Meta:
        unique_together = ("supplier", "supplier_article_no")
        verbose_name_plural = "All Products"

    def __str__(self):
        try:
            ret = f"SKU: {self.sku}, Name: {self.name}"
        except:
            ret = "Product"
        return ret

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

    @property
    def vat_rate(self):
        master_data = self.gls_master_data.first()
        if master_data:
            vat_rate = master_data.vat_rate
        else:
            raise ValueError(
                f"Product {self.sku} has no vat rate, perhaps it is not from GLS"
            )
        return vat_rate

    @property
    def stock(self):
        from apps.gls.models import GLSStockLevel

        if self.supplier == self.SUPPLIER_GLS:
            level = GLSStockLevel.objects.filter(
                article_no=self.supplier_article_no
            ).first()
            return float(level.inventory or 0) if level else 0.0

        non_gls = self.additional_master_data.first()
        return float(non_gls.stock or 0) if non_gls else 0.0

    @property
    def gtin(self):
        gtin = (
            ProductGtin.objects.filter(article_no=self.supplier_article_no)
            .values_list("gtin", flat=True)
            .first()
        )
        return gtin


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
    description = TextField(blank=True, null=True)
    active = BooleanField(default=True)
    width = CleanDecimalField(
        max_digits=14, decimal_places=4, help_text="unit(mm)", null=True, blank=True
    )
    height = CleanDecimalField(
        max_digits=14, decimal_places=4, help_text="unit(mm)", null=True, blank=True
    )
    length = CleanDecimalField(
        max_digits=14, decimal_places=4, help_text="unit(mm)", null=True, blank=True
    )
    weight = CleanDecimalField(
        max_digits=14, decimal_places=4, help_text="weight(g)", null=True, blank=True
    )
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


class ProductGtin(Model):
    SUPPLIER_GLS = "GLS"
    SUPPLIER_NON_GLS = "NON-GLS"

    article_no = CharField(max_length=100, db_index=True, null=True, blank=True)
    gtin = CharField(verbose_name="ean", max_length=200, null=True, blank=True)
    sku = CharField(max_length=200, db_index=True, null=True, blank=True)
    supplier = CharField(max_length=255, default=SUPPLIER_GLS, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Product GTIN"

    def __str__(self):
        return self.gtin or "gtin"

    def _supplier_obj(self):
        from apps.gls.models import GLSMasterData, GLSSupplier

        if self.supplier == self.SUPPLIER_GLS:
            md = GLSMasterData.objects.filter(article_no=self.article_no).first()
            if not md:
                return None
            return GLSSupplier.objects.filter(supplier_no=md.manufacturer).first()
        else:
            return None

    def product_safety_contact_name(self):
        s = self._supplier_obj()
        return s.name1 if s else None

    product_safety_contact_name.label = "product_safety_contact.name"
    product_safety_contact_name = property(product_safety_contact_name)

    def product_safety_contact_address(self):
        s = self._supplier_obj()
        if not s:
            return None

        parts = [
            s.street,
            s.postal_code,
            s.city,
            s.country.upper() if s.country else None,
        ]

        return ", ".join([p for p in parts if p])

    product_safety_contact_address.label = "product_safety_contact.address"
    product_safety_contact_address = property(product_safety_contact_address)

    def product_safety_contact_url(self):
        s = self._supplier_obj()
        return s.url if s else None

    product_safety_contact_url.label = "product_safety_contact.url"
    product_safety_contact_url = property(product_safety_contact_url)

    def product_safety_contact_email_address(self):
        s = self._supplier_obj()
        return s.email if s else None

    product_safety_contact_email_address.label = "product_safety_contact.email_address"
    product_safety_contact_email_address = property(
        product_safety_contact_email_address
    )

    def product_safety_contact_phone_number(self):
        s = self._supplier_obj()
        return s.phone if s else None

    product_safety_contact_phone_number.label = "product_safety_contact.phone_number"
    product_safety_contact_phone_number = property(product_safety_contact_phone_number)

    def locale(self):
        s = self._supplier_obj()
        country = s.country if s else None
        if not country:
            return None
        country = country.strip()
        return f"{country.lower()}-{country.upper()}"

    locale.label = "locale"
    locale = property(locale)


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


class MiddlewareSetting(Model):
    RULE_CHEAPEST = "cheapest"
    RULE_AVERAGE = "average"

    RULE_CHOICES = [
        (RULE_CHEAPEST, "Cheapest offer"),
        (RULE_AVERAGE, "Average of 3 cheapest offers"),
    ]

    minimum_margin = DecimalField(
        verbose_name="Global minimum margin in percentage (%)",
        max_digits=5,
        decimal_places=2,
        help_text="Eg 2.5%, 1.5%",
        default=0,
    )
    competitor_rule = CharField(
        verbose_name="Default competitor rule",
        max_length=20,
        default=RULE_CHEAPEST,
        choices=RULE_CHOICES,
    )
    undercut_value = DecimalField(
        max_digits=6,
        help_text="Amount to subtract from competitor price (x.xx €)",
        decimal_places=2,
        default=0,
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Middleware Settings"

    @property
    def normalised_minimum_margin(self):
        return self.minimum_margin / Decimal(100)


class ProductPriceHistory(Model):
    product = ForeignKey(
        Product, on_delete=models.CASCADE, related_name="price_history"
    )

    aera_sales_price = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    wawibox_sales_price = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    aera_gift_sales_price = DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    wawibox_gift_sales_price = DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    gift_min_qty = IntegerField(
        null=True,
        blank=True,
    )
    gift_paid_qty = IntegerField(null=True, blank=True)
    gift_free_qty = IntegerField(null=True, blank=True)
    gift_valid_from = DateField(blank=True, null=True)
    gift_valid_until = DateField(blank=True, null=True)
    calculated_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-calculated_at"]
        indexes = [
            models.Index(fields=["product", "-calculated_at"]),
            models.Index(fields=["calculated_at"]),
        ]
        verbose_name_plural = "Product Price History"

    def __str__(self):
        return f"{self.product_id} → {self.aera_sales_price} @ {self.calculated_at}"
