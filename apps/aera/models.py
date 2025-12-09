from django.db.models import Model
from django.db.models import ForeignKey
from django.db.models import OneToOneField
from django.db.models import CharField
from django.db.models import BooleanField
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


class AeraSession(Model):
    session_id = TextField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    def __str__(self):
        return self.session_id or "aera_session"


class AeraProduct(Model):
    """
    Holds product data fetched from Aera
    """

    product = OneToOneField(
        Product,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="aera_product",
    )
    sku = CharField(max_length=50, unique=True)
    aera_product_id = IntegerField(null=True, blank=True)
    manufacturer = CharField(max_length=255, blank=True, null=True)
    mpn = CharField(max_length=100, blank=True, null=True)

    offer_type_id = IntegerField(editable=False, null=True, blank=True)
    discontinuation = BooleanField(default=False)
    discontinuation_date = DateTimeField(null=True, blank=True)

    availability_type_id = IntegerField(
        null=True, blank=True, help_text="1=In stock, 2=Procurement Article"
    )
    different_delivery_time = IntegerField(
        verbose_name="Delivery time", null=True, blank=True
    )

    discountable = BooleanField(default=False)
    refundable = BooleanField(default=False)

    lower_bound_1 = IntegerField(null=True, blank=True)
    net_price_1 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    lower_bound_2 = IntegerField(null=True, blank=True)
    net_price_2 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    lower_bound_3 = IntegerField(null=True, blank=True)
    net_price_3 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    lower_bound_4 = IntegerField(null=True, blank=True)
    net_price_4 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    lower_bound_5 = IntegerField(null=True, blank=True)
    net_price_5 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    special_offer_valid_through = DateTimeField(null=True, blank=True)
    special_offer_discountable = BooleanField(default=False)

    special_offer_lower_bound_1 = IntegerField(null=True, blank=True)
    special_offer_net_price_1 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    special_offer_lower_bound_2 = IntegerField(null=True, blank=True)
    special_offer_net_price_2 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    special_offer_lower_bound_3 = IntegerField(null=True, blank=True)
    special_offer_net_price_3 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    special_offer_lower_bound_4 = IntegerField(null=True, blank=True)
    special_offer_net_price_4 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    special_offer_lower_bound_5 = IntegerField(null=True, blank=True)
    special_offer_net_price_5 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    shipped_temperature_stable = BooleanField(default=False)

    last_fetch_from_aera = DateTimeField(
        verbose_name="Last Fetched from AERA",
        help_text="Timestamp of the last data fetch from AERA",
        auto_now=True,
    )

    @property
    def offer_type_name(self):
        return OFFER_TYPE_ID_MAP.get(self.offer_type_id, "Unknown")

    class Meta:
        verbose_name = "Aera Product"
        verbose_name_plural = "Aera Products"

    def __str__(self):
        return self.sku


class AeraCompetitorPrice(Model):
    """
    Holds product competitor prices fetched from Aera
    """

    product = OneToOneField(
        Product,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="aera_competitor_price",
        editable=False,
    )
    sku = CharField(max_length=50, unique=True, db_index=True)
    net_own = DecimalField(
        verbose_name="Own Net Price",
        help_text="Net price from AERA for Jasado’s own offer",
        max_digits=12,
        decimal_places=2,
    )
    net_top_1 = DecimalField(
        verbose_name="Top 1 Net Price",
        help_text="Lowest competitor net price on AERA",
        max_digits=12,
        decimal_places=2,
    )
    net_top_2 = DecimalField(
        verbose_name="Top 2 Net Price",
        help_text="Second lowest competitor net price on AERA",
        max_digits=12,
        decimal_places=2,
    )
    net_top_3 = DecimalField(
        verbose_name="Top 3 Net Price",
        help_text="Third lowest competitor net price on AERA",
        max_digits=12,
        decimal_places=2,
    )

    last_fetch_from_aera = DateTimeField(
        verbose_name="Last Fetched from AERA",
        help_text="Timestamp of the last data fetch from AERA",
        auto_now=True,
    )

    class Meta:
        verbose_name = "AERA Competitor price"
        verbose_name_plural = "AERA Competitor prices"

    def __str__(self):
        return self.sku


class AeraExport(Model):
    """
    Holds product data pushed to Aera
    """

    sku = CharField(max_length=25, blank=True, null=True)
    product_name = CharField(max_length=255, blank=True, null=True)
    manufacturer = CharField(max_length=200, blank=True, null=True)
    mpn = CharField(max_length=25, blank=True, null=True)
    gtin = CharField(max_length=14, blank=True, null=True)
    offer_type_id = IntegerField(default=1, editable=False)
    availability_type_id = IntegerField(
        default=1, help_text="1=In stock, 2=Procurement Article"
    )
    different_delivery_time = IntegerField(
        verbose_name="Delivery time", default=0, help_text="Delivery time in days"
    )
    shipped_temperature_stable = BooleanField(default=True)
    weight = DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True, editable=False
    )
    sales_price = DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    updated_at = DateTimeField(auto_now=True)
    last_pushed_to_aera = DateTimeField(null=True, blank=True)

    @property
    def offer_type_name(self):
        return OFFER_TYPE_ID_MAP.get(self.offer_type_id, "Unknown")

    def __str__(self):
        return f"{self.sku} - {self.product_name or ''}"


class AeraOrder(Model):
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


class AeraOrderItem(Model):
    order = ForeignKey(AeraOrder, on_delete=CASCADE, related_name="items")
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
