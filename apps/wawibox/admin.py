from django.contrib import admin
from .models import (
    WawiboxProduct,
    WawiboxCompetitorPrice,
    WawiboxExport,
    WawiboxOrder,
    WawiboxOrderItem,
)


@admin.register(WawiboxProduct)
class WawiboxProductAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "name",
        "manufacturer_name",
        "manufacturer_part_number",
        "price",
        "delivery_time",
    )
    search_fields = ("sku", "name", "manufacturer_part_number")

    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "sku",
                    "name",
                )
            },
        ),
        (
            "Manufacturer Details",
            {
                "fields": (
                    "manufacturer_name",
                    "manufacturer_part_number",
                )
            },
        ),
        (
            "Primary Pricing",
            {
                "fields": (
                    "price",
                    "delivery_time",
                )
            },
        ),
        (
            "Tiered Pricing - Level 1",
            {
                "fields": (
                    "min_order_qty",
                    "min_order_qty_2",
                    "price_2",
                )
            },
        ),
        (
            "Tiered Pricing - Level 2",
            {
                "fields": (
                    "min_order_qty_3",
                    "price_3",
                )
            },
        ),
        (
            "Tiered Pricing - Level 3",
            {
                "fields": (
                    "min_order_qty_4",
                    "price_4",
                )
            },
        ),
        (
            "Tiered Pricing - Level 4",
            {
                "fields": (
                    "min_order_qty_5",
                    "price_5",
                )
            },
        ),
        (
            "Date",
            {"fields": ("last_fetch_from_wawibox",)},
        ),
    )

    def has_add_permission(self, r, o=None):
        return False

    def has_change_permission(self, r, o=None):
        return False

    def has_delete_permission(self, r, o=None):
        return False


@admin.register(WawiboxCompetitorPrice)
class WawiboxCompetitorPriceAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "product_name",
        "net_top_1",
        "net_top_2",
        "net_top_3",
    )
    search_fields = ("sku", "product_name")

    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "product",
                    "sku",
                    "product_name",
                )
            },
        ),
        (
            "Top Competitor 1",
            {
                "fields": (
                    "net_top_1",
                    "vendor_id_1",
                    "vendor_name_1",
                )
            },
        ),
        (
            "Top Competitor 2",
            {
                "fields": (
                    "net_top_2",
                    "vendor_id_2",
                    "vendor_name_2",
                )
            },
        ),
        (
            "Top Competitor 3",
            {
                "fields": (
                    "net_top_3",
                    "vendor_id_3",
                    "vendor_name_3",
                )
            },
        ),
        (
            "Top Competitor 4",
            {
                "fields": (
                    "net_top_4",
                    "vendor_id_4",
                    "vendor_name_4",
                )
            },
        ),
        (
            "Top Competitor 5",
            {
                "fields": (
                    "net_top_5",
                    "vendor_id_5",
                    "vendor_name_5",
                )
            },
        ),
        (
            "Top Competitor 6",
            {
                "fields": (
                    "net_top_6",
                    "vendor_id_6",
                    "vendor_name_6",
                )
            },
        ),
        (
            "Date",
            {"fields": ("last_fetch_from_wawibox",)},
        ),
    )

    def has_add_permission(self, r, o=None):
        return False

    def has_change_permission(self, r, o=None):
        return False

    def has_delete_permission(self, r, o=None):
        return False


@admin.register(WawiboxExport)
class WawiboxExportAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "internal_number",
        "manufacturer_article_no",
        "sales_price",
        "updated_at",
        "last_pushed_to_wawibox",
    )
    search_fields = (
        "name",
        "internal_number",
        "manufacturer_article_no",
    )

    def has_add_permission(self, r, o=None):
        return False

    def has_change_permission(self, r, o=None):
        return False

    def has_delete_permission(self, r, o=None):
        return False


# class WawiboxOrderItemInline(admin.TabularInline):
#     model = WawiboxOrderItem
#     extra = 0
#     can_delete = False
#     show_change_link = True
#     readonly_fields = [f.name for f in WawiboxOrderItem._meta.fields]


# @admin.register(WawiboxOrder)
# class WawiboxOrderAdmin(admin.ModelAdmin):
#     list_display = (
#         "order_token",
#         "order_number",
#         "buyer_name",
#         "seller_name",
#         "fetched_at",
#         "synced_to_weclapp",
#     )
#     search_fields = ("order_token", "order_number", "buyer_name", "seller_name")
#     list_filter = ("synced_to_weclapp",)

#     inlines = [WawiboxOrderItemInline]

#     def has_add_permission(self, r, o=None):
#         return False

#     def has_change_permission(self, r, o=None):
#         return False

#     def has_delete_permission(self, r, o=None):
#         return False


# @admin.register(WawiboxOrderItem)
# class WawiboxOrderItemAdmin(admin.ModelAdmin):
#     list_display = (
#         "order",
#         "sku",
#         "product_name",
#         "order_quantity",
#         "unit_price",
#         "total_price",
#         "vat_type_id",
#     )
#     search_fields = ("sku", "product_name", "order__order_number")

#     def has_add_permission(self, r, o=None):
#         return False

#     def has_change_permission(self, r, o=None):
#         return False

#     def has_delete_permission(self, r, o=None):
#         return False
