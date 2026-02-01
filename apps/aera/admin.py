from django.contrib import admin
from .models import (
    AeraProduct,
    AeraCompetitorPrice,
    AeraExport,
    AeraOrder,
    AeraOrderItem,
)


@admin.register(AeraProduct)
class AeraProductAdmin(admin.ModelAdmin):

    list_display = (
        "product__name",
        "sku",
        "aera_id",
    )

    search_fields = ("sku", "aera_id")
    list_per_page = 50

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


class AeraOrderItemInline(admin.TabularInline):
    model = AeraOrderItem
    extra = 0
    fields = (
        "sku",
        "product_name",
        "index_id",
        "order_quantity",
        "unit_price",
        "total_price",
        "discount_rate",
        "remark",
    )


@admin.register(AeraOrder)
class AeraOrderAdmin(admin.ModelAdmin):
    inlines = [AeraOrderItemInline]

    list_display = (
        "order_number",
        "buyer_name",
        "gross_amount",
        "date_transfer_released",
        "synced_to_weclapp",
    )
    list_display_links = (
        "order_number",
        "buyer_name",
        "gross_amount",
    )
    search_fields = ("order_number", "order_token", "buyer_name", "billing_email")

    fieldsets = (
        (
            "Order Info",
            {
                "fields": (
                    "order_number",
                    "order_token",
                    "buyer_name",
                    "currency",
                    "order_type_id",
                    "payment_method_id",
                    "note",
                )
            },
        ),
        (
            "Dates",
            {"fields": ("date_transfer_released",)},
        ),
        (
            "Billing Address",
            {
                "fields": (
                    "billing_name1",
                    "billing_name2",
                    "billing_line1",
                    "billing_line2",
                    "billing_city",
                    "billing_postcode",
                    "billing_country_code",
                    "billing_email",
                    "billing_phone",
                    "billing_vat_number",
                )
            },
        ),
        (
            "Delivery Address",
            {
                "fields": (
                    "delivery_name1",
                    "delivery_name2",
                    "delivery_line1",
                    "delivery_line2",
                    "delivery_city",
                    "delivery_postcode",
                    "delivery_country_code",
                    "delivery_email",
                    "delivery_phone",
                    "delivery_vat_number",
                )
            },
        ),
        (
            "Totals",
            {
                "fields": (
                    "net_amount",
                    "gross_amount",
                    "postage",
                    "company_vat_number",
                )
            },
        ),
        (
            "Sync Status",
            {
                "fields": (
                    "synced_to_weclapp",
                    "weclapp_id",
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
