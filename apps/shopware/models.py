from django.db.models import Model
from django.db.models import OneToOneField
from django.db.models import CharField
from django.db.models import BooleanField
from django.db.models import IntegerField
from django.db.models import TextField
from django.db.models import DateField
from django.db.models import DateTimeField
from django.db.models import DecimalField
from django.db.models import SET_NULL
from apps.core.models import Product
from django.utils import timezone
from datetime import timedelta


class AccessToken(Model):
    token = TextField(null=True, blank=True)
    refresh_token = TextField(null=True, blank=True)
    issued_at = DateTimeField()
    expires_in = IntegerField()

    def is_valid(self):
        buffer = 60
        expiration_time = self.issued_at + timedelta(seconds=self.expires_in - buffer)
        return expiration_time > timezone.now()


class ShopwareProduct(Model):
    """
    Holds product data fetched from Shopware
    """

    product = OneToOneField(
        Product,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="shopware_product",
    )
    shopware_id = CharField(
        max_length=200, unique=True, null=True, blank=True, db_index=True
    )
    sku = CharField(max_length=50, unique=True)
    name = CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Shopware Product"
        verbose_name_plural = "Shopware Products"

    def __str__(self):
        return self.sku


class ShopwareExport(Model):
    """
    Holds product data pushed to Shopware
    """

    shopware_id = CharField(
        max_length=200, unique=True, null=True, blank=True, db_index=True
    )
    sku = CharField(max_length=25, blank=True, null=True)
    name = CharField(max_length=255, blank=True, null=True)
    description = TextField(null=True, blank=True)
    sales_price = DecimalField(max_digits=14, decimal_places=4)
    gift_sales_price = DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    gift_min_qty = IntegerField(
        null=True, blank=True, help_text="Minimum quantity for gift price"
    )
    gift_paid_qty = IntegerField(null=True, blank=True)
    gift_free_qty = IntegerField(null=True, blank=True)
    gift_valid_from = DateField(blank=True, null=True)
    gift_valid_until = DateField(blank=True, null=True)
    manufacturer = CharField(max_length=200, blank=True, null=True)
    mpn = CharField(max_length=25, blank=True, null=True)
    gtin = CharField(max_length=14, blank=True, null=True)
    shipped_temperature_stable = BooleanField(default=True)
    length = DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    width = DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    height = DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    weight = DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    stock = DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    tax_rate = DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    updated_at = DateTimeField(auto_now=True)
    last_pushed_to_shopware = DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.sku} - {self.name or ''}"
