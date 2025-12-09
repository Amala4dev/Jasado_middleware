from django.contrib import admin
from .models import (
    AeraProduct,
    AeraCompetitorPrice,
    AeraExport,
)


@admin.register(AeraProduct)
class AeraProductAdmin(admin.ModelAdmin):

    list_display = (
        "sku",
        "manufacturer",
        "net_price_1",
        "different_delivery_time",
        "shipped_temperature_stable",
        "last_fetch_from_aera",
    )
    list_display_links = (
        "sku",
        "manufacturer",
        "net_price_1",
    )

    search_fields = ("sku", "manufacturer")
    list_per_page = 50

    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "product",
                    "sku",
                    "aera_product_id",
                    "manufacturer",
                    "mpn",
                )
            },
        ),
        (
            "Offer Details",
            {
                "fields": (
                    "offer_type_id",
                    "offer_type_name",
                    "discontinuation",
                    "discontinuation_date",
                )
            },
        ),
        (
            "Availability & Delivery",
            {
                "fields": (
                    "availability_type_id",
                    "different_delivery_time",
                    "shipped_temperature_stable",
                )
            },
        ),
        (
            "Standard Pricing",
            {
                "fields": (
                    ("lower_bound_1", "net_price_1"),
                    ("lower_bound_2", "net_price_2"),
                    ("lower_bound_3", "net_price_3"),
                    ("lower_bound_4", "net_price_4"),
                    ("lower_bound_5", "net_price_5"),
                )
            },
        ),
        (
            "Special Offer Pricing",
            {
                "fields": (
                    "special_offer_valid_through",
                    "special_offer_discountable",
                    ("special_offer_lower_bound_1", "special_offer_net_price_1"),
                    ("special_offer_lower_bound_2", "special_offer_net_price_2"),
                    ("special_offer_lower_bound_3", "special_offer_net_price_3"),
                    ("special_offer_lower_bound_4", "special_offer_net_price_4"),
                    ("special_offer_lower_bound_5", "special_offer_net_price_5"),
                )
            },
        ),
        (
            "Other Settings",
            {
                "fields": (
                    "discountable",
                    "refundable",
                    "last_fetch_from_aera",
                )
            },
        ),
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AeraCompetitorPrice)
class AeraCompetitorPriceAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "net_own",
        "net_top_1",
        "net_top_2",
        "net_top_3",
        "last_fetch_from_aera",
    )
    search_fields = ("sku", "product__name")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AeraExport)
class AeraExportAdmin(admin.ModelAdmin):
    list_display = (
        "product_name",
        "sku",
        "different_delivery_time",
        "sales_price",
        "updated_at",
        "last_pushed_to_aera",
    )
    list_display_links = ("sku", "product_name")
    search_fields = ("sku", "product_name", "manufacturer", "mpn", "gtin")
    list_per_page = 50

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
