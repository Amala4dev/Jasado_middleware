from django.db.models import Model
from django.db.models import ForeignKey
from django.db.models import OneToOneField
from django.db.models import CharField
from django.db.models import BooleanField
from django.db.models import DateField
from django.db.models import IntegerField
from django.db.models import TextField
from django.db.models import DateTimeField
from django.db.models import DecimalField
from django.db.models import SET_NULL
from django.db.models import CASCADE
from apps.core.models import Product

OFFER_TYPE_ID_MAP = {
    1: "Default",
    3: "New",
    4: "Free",
    5: "Opening offer",
    7: "Discontinued item",
}


class WawiboxProduct(Model):
    """
    Holds product data fetched from Wawibox
    """

    product = OneToOneField(
        Product,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="wawibox_product",
        editable=False,
    )

    sku = CharField(max_length=50, unique=True)
    name = CharField(max_length=255, blank=True, null=True)
    manufacturer_name = CharField(max_length=255, blank=True, null=True)
    manufacturer_part_number = CharField(max_length=100, blank=True, null=True)

    price = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    delivery_time = CharField(max_length=50, blank=True, null=True)

    min_order_qty = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    min_order_qty_2 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    price_2 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    min_order_qty_3 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    price_3 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    min_order_qty_4 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    price_4 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    min_order_qty_5 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    price_5 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    last_fetch_from_wawibox = DateTimeField(
        verbose_name="Last Fetched from Wawibox",
        help_text="Timestamp of the last data fetch from Wawibox",
        auto_now=True,
    )

    class Meta:
        verbose_name = "Wawibox Product"
        verbose_name_plural = "Wawibox Products"

    def __str__(self):
        return self.sku


class WawiboxCompetitorPrice(Model):
    """
    Holds product competitor prices fetched from Wawibox
    """

    JASADO_VENDOR_ID = "468312"

    product = ForeignKey(
        Product,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="wawibox_competitor_price",
        editable=False,
    )

    sku = CharField(max_length=50, blank=True, null=True, db_index=True)
    product_name = CharField(max_length=255, blank=True, null=True)

    net_top_1 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )  # price1
    vendor_id_1 = CharField(max_length=50, null=True, blank=True)
    vendor_name_1 = CharField(max_length=255, null=True, blank=True)

    net_top_2 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )  # price2
    vendor_id_2 = CharField(max_length=50, null=True, blank=True)
    vendor_name_2 = CharField(max_length=255, null=True, blank=True)

    net_top_3 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )  # price3
    vendor_id_3 = CharField(max_length=50, null=True, blank=True)
    vendor_name_3 = CharField(max_length=255, null=True, blank=True)

    net_top_4 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )  # price4
    vendor_id_4 = CharField(max_length=50, null=True, blank=True)
    vendor_name_4 = CharField(max_length=255, null=True, blank=True)

    net_top_5 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    vendor_id_5 = CharField(max_length=50, null=True, blank=True)
    vendor_name_5 = CharField(max_length=255, null=True, blank=True)

    net_top_6 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    vendor_id_6 = CharField(max_length=50, null=True, blank=True)
    vendor_name_6 = CharField(max_length=255, null=True, blank=True)

    last_fetch_from_wawibox = DateTimeField(
        verbose_name="Last Fetched from Wawibox",
        help_text="Timestamp of the last data fetch from Wawibox",
        auto_now=True,
    )

    class Meta:
        verbose_name = "Wawibox Competitor price"
        verbose_name_plural = "Wawibox Competitor prices"

    def __str__(self):
        return self.sku


class WawiboxExport(Model):
    manufacturer_article_no = CharField(
        max_length=50, blank=True, null=True, db_index=True
    )
    manufacturer_name = CharField(max_length=255, blank=True, null=True, editable=False)
    private_label = BooleanField(default=False, editable=False)
    internal_number = CharField(max_length=100, db_index=True)
    name = CharField(max_length=255, blank=True, null=True)
    description = TextField(blank=True, null=True, editable=False)
    vat_category = IntegerField(
        help_text="0 = Full, 1 = Reduced, 2 = None",
        blank=True,
        null=True,
        editable=False,
    )
    max_order_quantity = IntegerField(null=True, blank=True, editable=False)
    image1_url = CharField(max_length=255, blank=True, null=True, editable=False)
    image2_url = CharField(max_length=255, blank=True, null=True, editable=False)
    image3_url = CharField(max_length=255, blank=True, null=True, editable=False)
    returnable = BooleanField(
        default=False, help_text="0 = non-returnable, 1 = returnable", editable=False
    )
    is_available = BooleanField(
        default=False,
        help_text="0 = currently out of stock, 1 = currently in stock.",
        editable=False,
    )
    delivery_time = IntegerField(null=True, blank=True, editable=False)
    order_number = CharField(
        max_length=100, blank=True, null=True, editable=False
    )  # unique number to identify the price offer
    valid_from = DateField(null=True, blank=True, editable=False)
    valid_until = DateField(null=True, blank=True, editable=False)
    min_order_quantity = IntegerField(null=True, blank=True, editable=False)
    sales_price = DecimalField(max_digits=14, decimal_places=4)
    discountable = BooleanField(
        default=False,
        help_text="0 = not eligible for discount, 1 = eligible for discount.",
        editable=False,
    )
    # For tier pricing fill below fields
    order_number_2 = CharField(max_length=100, blank=True, null=True, editable=False)
    min_order_quantity_2 = IntegerField(null=True, blank=True, editable=False)
    price_2 = DecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True, editable=False
    )
    discountable_2 = BooleanField(
        default=False,
        help_text="0 = not eligible for discount, 1 = eligible for discount.",
        editable=False,
    )
    updated_at = DateTimeField(auto_now=True)
    last_pushed_to_wawibox = DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.internal_number} - {self.name or ''}"


class WawiboxOrder(Model):
    order_token = CharField(max_length=100, unique=True)
    order_number = CharField(max_length=100, null=True, blank=True)
    buyer_name = CharField(max_length=255, null=True, blank=True)
    seller_name = CharField(max_length=255, null=True, blank=True)
    date_transfer_confirmed = DateTimeField(null=True, blank=True)
    date_transfer_released = DateTimeField(null=True, blank=True)
    fetched_at = DateTimeField(null=True, blank=True)
    synced_to_weclapp = BooleanField(default=False, db_index=True)

    # Billing address
    billing_name1 = CharField(max_length=255, null=True, blank=True)
    billing_name2 = CharField(max_length=255, null=True, blank=True)
    billing_line1 = CharField(max_length=255, null=True, blank=True)
    billing_line2 = CharField(max_length=255, null=True, blank=True)
    billing_city = CharField(max_length=100, null=True, blank=True)
    billing_postcode = CharField(max_length=50, null=True, blank=True)
    billing_country_code = CharField(max_length=10, null=True, blank=True)
    billing_email = CharField(max_length=255, null=True, blank=True)
    billing_phone = CharField(max_length=50, null=True, blank=True)
    billing_vat_number = CharField(max_length=100, null=True, blank=True)

    # Delivery address
    delivery_name1 = CharField(max_length=255, null=True, blank=True)
    delivery_name2 = CharField(max_length=255, null=True, blank=True)
    delivery_line1 = CharField(max_length=255, null=True, blank=True)
    delivery_line2 = CharField(max_length=255, null=True, blank=True)
    delivery_city = CharField(max_length=100, null=True, blank=True)
    delivery_postcode = CharField(max_length=50, null=True, blank=True)
    delivery_country_code = CharField(max_length=10, null=True, blank=True)
    delivery_email = CharField(max_length=255, null=True, blank=True)
    delivery_phone = CharField(max_length=50, null=True, blank=True)
    delivery_vat_number = CharField(max_length=100, null=True, blank=True)

    # Totals and other details
    currency = CharField(max_length=10, null=True, blank=True)
    gross_amount = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    net_amount = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    vat_amount_full = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    vat_amount_half = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    vat_rate_full = DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    vat_rate_half = DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    postage = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    payment_method_id = IntegerField(null=True, blank=True)
    order_type_id = IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.order_number or self.order_token}"


class WawiboxOrderItem(Model):
    order = ForeignKey(WawiboxOrder, on_delete=CASCADE, related_name="items")
    sku = CharField(max_length=100, null=True, blank=True)
    product_name = CharField(max_length=255, null=True, blank=True)
    product_id = IntegerField(null=True, blank=True)
    order_quantity = IntegerField(null=True, blank=True)
    total_quantity = IntegerField(null=True, blank=True)
    unit_price = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_price = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_value_of_goods = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    unit_of_measure = CharField(max_length=50, null=True, blank=True)
    discount_rate = DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    vat_type_id = IntegerField(null=True, blank=True)
    remark = TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.sku or ''} - {self.product_name or ''}"
