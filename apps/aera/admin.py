from django.contrib import admin
from .models import (
    AeraSession,
    AeraProduct,
    AeraCompetitorPrice,
    AeraOrder,
    AeraProductUpdate,
)


# @admin.register(AeraSession)
# class AeraSessionAdmin(admin.ModelAdmin):

#     list_display = ("session_id", "created_at", "updated_at")
#     list_display_links = ("session_id", "created_at", "updated_at")
#     search_fields = ("session_id",)

#     def has_add_permission(self, request, obj=None):
#         return False

#     def has_change_permission(self, request, obj=None):
#         return False

#     def has_delete_permission(self, request, obj=None):
#         return False


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


# @admin.register(AeraOrder)
# class AeraOrderAdmin(admin.ModelAdmin):

#     list_display = ("order_number", "buyer_name", "fetched_at", "synced_to_weclapp")
#     list_display_links = (
#         "order_number",
#         "buyer_name",
#         "fetched_at",
#         "synced_to_weclapp",
#     )
#     list_filter = ("synced_to_weclapp",)
#     search_fields = (
#         "order_token",
#         "order_number",
#         "buyer_name",
#         "seller_name",
#     )
#     list_per_page = 50

#     def has_add_permission(self, request, obj=None):
#         return False

#     def has_change_permission(self, request, obj=None):
#         return False

#     def has_delete_permission(self, request, obj=None):
#         return False


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


# @admin.register(AeraProductUpdate)
# class AeraProductUpdateAdmin(admin.ModelAdmin):
#     list_display = (
#         "sku",
#         "product_name",
#         "manufacturer",
#         "mpn",
#         "different_delivery_time",
#         "shipped_temperature_stable",
#         "calculated_sales_price",
#         "created_at",
#     )
#     list_display_links = ("sku", "product_name", "manufacturer")
#     search_fields = ("sku", "product_name", "manufacturer", "mpn", "gtin")
#     list_per_page = 50

#     def has_add_permission(self, request, obj=None):
#         return False

#     def has_change_permission(self, request, obj=None):
#         return False

#     def has_delete_permission(self, request, obj=None):
#         return False
