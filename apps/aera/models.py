from django.db.models import Model
from django.db.models import ForeignKey
from django.db.models import OneToOneField
from django.db.models import CharField
from django.db.models import BooleanField
from django.db.models import IntegerField
from django.db.models import TextField
from django.db.models import DateTimeField
from django.db.models import DecimalField
from django.db.models import DateField
from django.db.models import SET_NULL
from django.db.models import CASCADE
from apps.core.models import Product
from apps.weclapp.client import fetch_article_by_sku
from utils import (
    to_unix_ms,
    weclapp_sales_channel,
    truncate_max_length,
    clean_payload,
    OrderBaseModel,
)
from django.conf import settings

WECLAPP_SHIPPING_ARTICLE_MAP = settings.WECLAPP_SHIPPING_ARTICLE_MAP

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
    aera_id = IntegerField(null=True, blank=True)

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
        max_digits=12, decimal_places=2, null=True, blank=True, editable=False
    )
    sales_price = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    gift_sales_price = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    gift_min_qty = IntegerField(
        null=True, blank=True, help_text="Minimum quantity for gift price"
    )
    gift_valid_until = DateField(blank=True, null=True)
    updated_at = DateTimeField(auto_now=True)
    last_pushed_to_aera = DateTimeField(
        verbose_name="Date pushed to aera", null=True, blank=True
    )

    @property
    def offer_type_name(self):
        return OFFER_TYPE_ID_MAP.get(self.offer_type_id, "Unknown")

    def __str__(self):
        return f"{self.sku} - {self.product_name or ''}"


class AeraOrder(OrderBaseModel):
    order_token = CharField(max_length=100, unique=True)
    buyer_name = CharField(max_length=255, null=True, blank=True)
    date_transfer_released = DateTimeField(null=True, blank=True)
    note = CharField(max_length=255, null=True, blank=True)

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
    company_vat_number = CharField(max_length=100, null=True, blank=True)
    currency = CharField(max_length=10, null=True, blank=True)
    gross_amount = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    net_amount = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    postage = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    payment_method_id = IntegerField(null=True, blank=True)
    order_type_id = IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.order_number or self.order_token}"

    class Meta:
        ordering = ["-date_transfer_released"]

    @property
    def customer_email(self):
        return self.billing_email

    def build_weclapp_order_payload(self, customer_id):
        items = list(self.items.all())

        skus = {item.sku for item in items}

        product_map = {p.sku: p for p in Product.objects.filter(sku__in=skus)}

        payload = {
            "customerId": customer_id,
            "orderNumberAtCustomer": self.order_number,
            "orderDate": (
                to_unix_ms(self.date_transfer_released)
                if self.date_transfer_released
                else None
            ),
            "note": truncate_max_length(self.note, 512),
            "salesChannel": weclapp_sales_channel().get("AERA"),
            "invoiceAddress": {
                "company": self.billing_name1,
                "company2": self.billing_name2,
                "street1": self.billing_line1,
                "street2": self.billing_line2,
                "city": self.billing_city,
                "zipcode": self.billing_postcode,
                "countryCode": self.billing_country_code,
                "phoneNumber": self.billing_phone,
            },
            "deliveryAddress": {
                "company": self.delivery_name1,
                "company2": self.delivery_name2,
                "street1": self.delivery_line1,
                "street2": self.delivery_line2,
                "city": self.delivery_city,
                "zipcode": self.delivery_postcode,
                "countryCode": self.delivery_country_code,
                "phoneNumber": self.delivery_phone,
            },
            "deliveryEmailAddresses": {
                "toAddresses": self.delivery_email,
            },
            "orderItems": [],
            "shippingCostItems": [
                {
                    "articleId": fetch_article_by_sku(
                        WECLAPP_SHIPPING_ARTICLE_MAP[self.delivery_country_code]
                    )["id"],
                    "manualUnitPrice": True,
                    "unitPrice": self.postage,
                }
            ],
        }

        order_items = [
            {
                "articleId": product_map[item.sku].weclapp_id,
                "positionNumber": item.index_id,
                "quantity": item.order_quantity,
                "unitPrice": item.unit_price,
                "manualUnitPrice": True,
                "discountPercentage": item.discount_rate,
                "note": truncate_max_length(item.remark, 1000),
            }
            for item in items
        ]

        next_pos = max(i["positionNumber"] for i in order_items)

        # ADD PROMOTION FREE LINE
        for item in items:
            product = product_map[item.sku]
            order_qty = item.order_quantity
            if product.has_gift_price and (order_qty >= product.gift_min_qty):
                blocks = order_qty // product.gift_min_qty
                free_qty = blocks * product.gift_free_qty

                next_pos += 1
                order_items.append(
                    {
                        "articleId": product_map[item.sku].weclapp_id,
                        "positionNumber": next_pos,
                        "quantity": free_qty,
                        "unitPrice": -item.unit_price,
                        "manualUnitPrice": True,
                        "manualUnitCost": True,
                        "unitCost": 0,
                    }
                )

        payload["orderItems"] = order_items

        payload = clean_payload(payload)
        return payload

    def build_weclapp_customer_payload(self):
        payload = {
            "partyType": "ORGANIZATION",
            "customer": True,
            "company": self.buyer_name,
            "email": self.billing_email,
            "phone": self.billing_phone,
            "vatIdentificationNumber": self.company_vat_number
            or self.billing_vat_number
            or self.delivery_vat_number,
            "addresses": [
                {
                    "primaryAddress": True,
                    "invoiceAddress": True,
                    "deliveryAddress": False,
                    "company": self.billing_name1,
                    "street1": self.billing_line1,
                    "street2": self.billing_line2,
                    "city": self.billing_city,
                    "zipcode": self.billing_postcode,
                    "countryCode": self.billing_country_code,
                    "phoneNumber": self.billing_phone,
                },
                {
                    "primaryAddress": False,
                    "invoiceAddress": False,
                    "deliveryAddress": True,
                    "company": self.delivery_name1,
                    "street1": self.delivery_line1,
                    "street2": self.delivery_line2,
                    "city": self.delivery_city,
                    "zipcode": self.delivery_postcode,
                    "countryCode": self.delivery_country_code,
                    "phoneNumber": self.delivery_phone,
                },
            ],
        }
        payload = clean_payload(payload)
        return payload


class AeraOrderItem(Model):
    order = ForeignKey(AeraOrder, on_delete=CASCADE, related_name="items")
    sku = CharField(max_length=100, null=True, blank=True)
    product_name = CharField(max_length=255, null=True, blank=True)
    product_id = IntegerField(null=True, blank=True)
    index_id = IntegerField(verbose_name="Position", null=True, blank=True)
    order_quantity = IntegerField(null=True, blank=True)
    unit_price = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_price = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_rate = DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    discount_amount = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    vat_type_id = IntegerField(null=True, blank=True)
    remark = TextField(null=True, blank=True)

    def __str__(self):
        return ""
