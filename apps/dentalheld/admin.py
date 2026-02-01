from django.contrib import admin

from .models import (
    DentalheldOrder,
    DentalheldOrderItem,
    DentalheldExport,
)


@admin.register(DentalheldExport)
class DentalheldExportAdmin(admin.ModelAdmin):
    list_display = (
        "article_id",
        "name",
        "net_price",
        "tier_qty_1",
        "tier_price_1",
        "last_pushed_to_dentalheld",
    )
    list_display_links = list_display
    search_fields = ("article_id", "name")
    list_per_page = 50

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DentalheldOrderItemInline(admin.TabularInline):
    model = DentalheldOrderItem
    extra = 0
    fields = (
        "sku",
        "name",
        "quantity",
        "price",
        "tax",
        "packing_unit",
        "packing_size",
    )


@admin.register(DentalheldOrder)
class DentalheldOrderAdmin(admin.ModelAdmin):
    inlines = [DentalheldOrderItemInline]

    list_display = (
        "order_number",
        "user_name",
        "gross_amount",
        "created_at",
        "synced_to_weclapp",
    )
    list_display_links = list_display

    search_fields = (
        "order_number",
        "user_name",
        "user_email",
        "customer_number",
    )

    fieldsets = (
        (
            "Order Info",
            {
                "fields": (
                    "order_number",
                    "user_salutation",
                    "user_prename",
                    "user_name",
                    "user_email",
                    "user_phone",
                    "user_type",
                    "comment",
                )
            },
        ),
        (
            "Dates",
            {"fields": ("created_at",)},
        ),
        (
            "Billing Address",
            {
                "fields": (
                    "billing_salutation",
                    "billing_prename",
                    "billing_name",
                    "billing_company",
                    "billing_street",
                    "billing_street_nr",
                    "billing_location",
                    "billing_zipcode",
                    "billing_country",
                )
            },
        ),
        (
            "Delivery Address",
            {
                "fields": (
                    "delivery_salutation",
                    "delivery_prename",
                    "delivery_name",
                    "delivery_company",
                    "delivery_street",
                    "delivery_street_nr",
                    "delivery_location",
                    "delivery_zipcode",
                    "delivery_country",
                )
            },
        ),
        (
            "Totals",
            {
                "fields": (
                    "net_amount",
                    "gross_amount",
                    "tax",
                    "shipping_costs",
                    "low_quantity_surcharge",
                    "user_tax_number",
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
