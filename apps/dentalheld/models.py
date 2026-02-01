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


class DentalheldProduct(Model):
    product = OneToOneField(
        Product,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="dentalheld_product",
    )
    sku = CharField(max_length=100, unique=True)  # article_id
    ean = CharField(max_length=50, null=True, blank=True)
    name = CharField(max_length=255, null=True, blank=True)
    net_price = DecimalField(max_digits=12, decimal_places=2)
    manufacturer_id = CharField(max_length=100, null=True, blank=True)
    manufacturer_name = CharField(max_length=255, null=True, blank=True)
    manufacturer_article_number = CharField(max_length=100, null=True, blank=True)
    delivery_status = IntegerField(
        null=True,
        blank=True,
        help_text="0 = currently unavailable, 1 = available soon, 2 = available immediately",
    )
    delivery_time_days = IntegerField(null=True, blank=True)
    stock_level = IntegerField(
        null=True,
        blank=True,
        help_text="0 = red order status, 1-4 = yellow order status, >4 = green order status",
    )
    temperature_shipping_cost = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    extra_cost_max = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    extra_cost_additive = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    tier_qty_1 = IntegerField(null=True, blank=True)
    tier_price_1 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    tier_qty_2 = IntegerField(null=True, blank=True)
    tier_price_2 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    tier_qty_3 = IntegerField(null=True, blank=True)
    tier_price_3 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    tier_qty_4 = IntegerField(null=True, blank=True)
    tier_price_4 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    tier_qty_5 = IntegerField(null=True, blank=True)
    tier_price_5 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    returnable = BooleanField(default=False)
    student_net_price = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    student_tier_qty_1 = IntegerField(null=True, blank=True)
    student_tier_price_1 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    student_tier_qty_2 = IntegerField(null=True, blank=True)
    student_tier_price_2 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    student_tier_qty_3 = IntegerField(null=True, blank=True)
    student_tier_price_3 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    student_tier_qty_4 = IntegerField(null=True, blank=True)
    student_tier_price_4 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    student_tier_qty_5 = IntegerField(null=True, blank=True)
    student_tier_price_5 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    search_keywords = TextField(null=True, blank=True)
    comparable_product_urls = TextField(null=True, blank=True)

    updated_at = DateTimeField(auto_now=True)

    def __str__(self):
        return self.article_id


class DentalheldExport(Model):
    """
    Holds product data pushed to Dentalheld
    """

    article_id = CharField("Sku", max_length=100, unique=True)
    ean = CharField(max_length=50, null=True, blank=True)
    name = CharField(max_length=255, null=True, blank=True)
    net_price = DecimalField(max_digits=12, decimal_places=2)
    manufacturer_id = CharField(max_length=100, null=True, blank=True)
    manufacturer_name = CharField(max_length=255, null=True, blank=True)
    manufacturer_article_number = CharField(max_length=100, null=True, blank=True)
    delivery_status = IntegerField(
        null=True,
        blank=True,
        help_text="0 = currently unavailable, 1 = available soon, 2 = available immediately",
    )
    delivery_time_days = IntegerField(null=True, blank=True)
    stock_level = IntegerField(
        null=True,
        blank=True,
        help_text="0 = red order status, 1-4 = yellow order status, >4 = green order status",
    )
    temperature_shipping_cost = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    extra_cost_max = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    extra_cost_additive = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    tier_qty_1 = IntegerField(null=True, blank=True)
    tier_price_1 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    tier_qty_2 = IntegerField(null=True, blank=True)
    tier_price_2 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    tier_qty_3 = IntegerField(null=True, blank=True)
    tier_price_3 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    tier_qty_4 = IntegerField(null=True, blank=True)
    tier_price_4 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    tier_qty_5 = IntegerField(null=True, blank=True)
    tier_price_5 = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    returnable = BooleanField(default=False)
    student_net_price = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    student_tier_qty_1 = IntegerField(null=True, blank=True)
    student_tier_price_1 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    student_tier_qty_2 = IntegerField(null=True, blank=True)
    student_tier_price_2 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    student_tier_qty_3 = IntegerField(null=True, blank=True)
    student_tier_price_3 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    student_tier_qty_4 = IntegerField(null=True, blank=True)
    student_tier_price_4 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    student_tier_qty_5 = IntegerField(null=True, blank=True)
    student_tier_price_5 = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    search_keywords = TextField(null=True, blank=True)
    comparable_product_urls = TextField(null=True, blank=True)

    updated_at = DateTimeField(auto_now=True)
    last_pushed_to_dentalheld = DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.article_id


class DentalheldOrder(OrderBaseModel):
    user_salutation = CharField(max_length=20, null=True, blank=True)
    user_prename = CharField(max_length=255, null=True, blank=True)
    user_name = CharField(max_length=255, null=True, blank=True)
    user_email = CharField(max_length=255, null=True, blank=True)
    user_phone = CharField(max_length=50, null=True, blank=True)
    comment = CharField(max_length=255, null=True, blank=True)
    created_at = DateTimeField(null=True, blank=True)
    cancelled = BooleanField(default=False)
    customer_number = CharField(max_length=100, null=True, blank=True)
    merchant_customer_number = CharField(max_length=100, null=True, blank=True)
    user_type = CharField(max_length=50, null=True, blank=True)
    user_tax_number = CharField(max_length=100, null=True, blank=True)

    # Billing address
    billing_salutation = CharField(max_length=20, null=True, blank=True)
    billing_prename = CharField(max_length=255, null=True, blank=True)
    billing_name = CharField(max_length=255, null=True, blank=True)
    billing_company = CharField(max_length=255, null=True, blank=True)
    billing_street = CharField(max_length=255, null=True, blank=True)
    billing_street_nr = CharField(max_length=255, null=True, blank=True)
    billing_location = CharField(max_length=100, null=True, blank=True)
    billing_zipcode = CharField(max_length=50, null=True, blank=True)
    billing_country = CharField(max_length=10, null=True, blank=True)

    # Delivery address
    delivery_salutation = CharField(max_length=20, null=True, blank=True)
    delivery_prename = CharField(max_length=255, null=True, blank=True)
    delivery_name = CharField(max_length=255, null=True, blank=True)
    delivery_company = CharField(max_length=255, null=True, blank=True)
    delivery_street = CharField(max_length=255, null=True, blank=True)
    delivery_street_nr = CharField(max_length=255, null=True, blank=True)
    delivery_location = CharField(max_length=100, null=True, blank=True)
    delivery_zipcode = CharField(max_length=50, null=True, blank=True)
    delivery_country = CharField(max_length=10, null=True, blank=True)

    # Totals
    gross_amount = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    net_amount = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tax = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    shipping_costs = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    low_quantity_surcharge = DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    def __str__(self):
        return self.order_number

    class Meta:
        ordering = ["-created_at"]

    @property
    def customer_email(self):
        return self.user_email

    def build_weclapp_order_payload(self, customer_id):
        items = list(self.items.all())

        skus = {item.sku for item in items}
        product_map = {p.sku: p for p in Product.objects.filter(sku__in=skus)}

        payload = {
            "customerId": customer_id,
            "orderNumberAtCustomer": self.order_number,
            "orderDate": to_unix_ms(self.created_at) if self.created_at else None,
            "note": truncate_max_length(self.comment, 512),
            "salesChannel": weclapp_sales_channel().get("DENTALHELD"),
            "invoiceAddress": {
                "company": self.billing_name,
                "company2": self.billing_company,
                "street1": self.billing_street_nr,
                "street2": self.billing_street,
                "city": self.billing_location,
                "zipcode": self.billing_zipcode,
                "countryCode": self.billing_country,
                "phoneNumber": self.user_phone,
            },
            "deliveryAddress": {
                "company": self.delivery_name,
                "company2": self.delivery_company,
                "street1": self.delivery_street_nr,
                "street2": self.delivery_street,
                "city": self.delivery_location,
                "zipcode": self.delivery_zipcode,
                "countryCode": self.delivery_country,
                "phoneNumber": self.user_phone,
            },
            "deliveryEmailAddresses": {
                "toAddresses": self.user_email,
            },
            "orderItems": [],
            "shippingCostItems": [
                {
                    "articleId": fetch_article_by_sku(
                        WECLAPP_SHIPPING_ARTICLE_MAP[self.delivery_country]
                    )["id"],
                    "manualUnitPrice": True,
                    "unitPrice": self.shipping_costs,
                }
            ],
        }

        order_items = [
            {
                "articleId": product_map[item.sku].weclapp_id,
                "positionNumber": i + 1,
                "quantity": item.quantity,
                "unitPrice": item.price,
                "manualUnitPrice": True,
            }
            for i, item in enumerate(items)
        ]
        next_pos = max(i["positionNumber"] for i in order_items)

        # ADD PROMOTION FREE LINE
        for item in items:
            product = product_map[item.sku]
            order_qty = item.quantity
            if product.has_gift_price and (order_qty >= product.gift_min_qty):
                blocks = order_qty // product.gift_min_qty
                free_qty = blocks * product.gift_free_qty

                next_pos += 1
                order_items.append(
                    {
                        "articleId": product_map[item.sku].weclapp_id,
                        "positionNumber": next_pos,
                        "quantity": free_qty,
                        "unitPrice": -item.price,
                        "manualUnitPrice": True,
                        "manualUnitCost": True,
                        "unitCost": 0,
                    }
                )

        payload["orderItems"] = order_items
        return clean_payload(payload)

    def build_weclapp_customer_payload(self):
        payload = {
            "partyType": "ORGANIZATION",
            "customer": True,
            "company": self.billing_company,
            "email": self.user_email,
            "phone": self.user_phone,
            "vatIdentificationNumber": self.user_tax_number,
            "addresses": [
                {
                    "primaryAddress": True,
                    "invoiceAddress": True,
                    "deliveryAddress": False,
                    "company": self.billing_company,
                    "street1": self.billing_street_nr,
                    "street2": self.billing_street,
                    "city": self.billing_location,
                    "zipcode": self.billing_zipcode,
                    "countryCode": self.billing_country,
                    "phoneNumber": self.user_phone,
                },
                {
                    "primaryAddress": False,
                    "invoiceAddress": False,
                    "deliveryAddress": True,
                    "company": self.delivery_company,
                    "street1": self.delivery_street_nr,
                    "street2": self.delivery_street,
                    "city": self.delivery_location,
                    "zipcode": self.delivery_zipcode,
                    "countryCode": self.delivery_country,
                    "phoneNumber": self.user_phone,
                },
            ],
        }

        return clean_payload(payload)


class DentalheldOrderItem(Model):
    order = ForeignKey(DentalheldOrder, on_delete=CASCADE, related_name="items")
    article_id = IntegerField(null=True, blank=True)
    sku = CharField(max_length=100, null=True, blank=True)
    name = CharField(max_length=255, null=True, blank=True)
    manufacturer = CharField(max_length=255, null=True, blank=True)
    price = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    quantity = IntegerField(null=True, blank=True)
    packing_unit = CharField(max_length=50, null=True, blank=True)
    packing_size = CharField(max_length=50, null=True, blank=True)
    tax = DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    merchant_article_id = CharField(max_length=100, null=True, blank=True)
    merchant_manufacturer_id = CharField(max_length=100, null=True, blank=True)
    was_taxed = BooleanField(default=False)
    cancelled = BooleanField(default=False)

    def __str__(self):
        return ""
