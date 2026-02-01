from django.contrib import admin
from .models import (
    ShopwareProduct,
    ShopwareExport,
)


@admin.register(ShopwareProduct)
class ShopwareProductAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "sku",
        "shopware_id",
    )

    search_fields = ("sku", "shopware_id")
    list_per_page = 50

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ShopwareExport)
class ShopwareExportAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "sales_price",
        "updated_at",
        "last_pushed_to_shopware",
    )
    list_display_links = ("name", "sku")
    search_fields = ("sku", "name")
    list_per_page = 50

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
