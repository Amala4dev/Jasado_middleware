from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import (
    LogEntry,
    AdditionalMasterData,
    BlockedProduct,
    ExportTask,
    Product,
    MiddlewareSetting,
    ProductPriceHistory,
    ProductGtin,
)
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

admin.site.unregister(Group)
admin.site.unregister(User)


class CustomAppOrderAdminSite(admin.AdminSite):
    def get_app_list(self, request, app_label=None):
        """
        Return a sorted list of all the installed apps that have been
        registered in this site.
        """
        model_ordering_core = {
            "Product": 1,
            "AdditionalMasterData": 2,
            "BlockedProduct": 3,
            "ProductGtin": 4,
            "ExportTask": 5,
            "MiddlewareSetting": 6,
            "LogEntry": 7,
            "ProductPriceHistory": 8,
        }

        model_ordering_aera = {
            "AeraProduct": 1,
            "AeraCompetitorPrice": 2,
            "AeraExport": 3,
        }

        model_ordering_gls = {
            "GLSMasterData": 1,
            "GLSStockLevel": 2,
            "GLSPriceList": 3,
            "GLSPromotionHeader": 4,
            "GLSPromotionPosition": 5,
            "GLSPromotionPrice": 6,
            "GLSSupplier": 7,
            "GLSOrderConfirmation": 8,
            "GLSBackorder": 9,
            "GLSOrderStatus": 10,
            "GLSHandlingSurcharge": 11,
            "GLSProductGroup": 12,
        }

        model_ordering_wawibox = {
            "WawiboxProduct": 1,
            "WawiboxCompetitorPrice": 2,
            "WawiboxExport": 3,
        }

        app_dict = self._build_app_dict(request, app_label)

        # Sort the apps alphabetically.
        app_list = sorted(app_dict.values(), key=lambda x: x["name"].lower())

        app_ordering = {
            "core": 1,
            "aera": 2,
            "gls": 3,
            "wawibox": 4,
            "weclapp": 5,
            "auth": 6,
        }
        app_list.sort(key=lambda x: app_ordering.get(x["app_label"], 999))
        app_model_to_sort = {"core", "aera", "gls", "wawibox"}
        model_order_map = {
            "core": model_ordering_core,
            "aera": model_ordering_aera,
            "gls": model_ordering_gls,
            "wawibox": model_ordering_wawibox,
        }
        for app in app_list:
            app_label = app["app_label"]
            if app_label == "auth":
                app["name"] = "User Management"

            if app_label in app_model_to_sort:
                model_ordering = model_order_map[app_label]
                app["models"].sort(key=lambda x: model_ordering[x["object_name"]])

        return app_list


admin.site.__class__ = CustomAppOrderAdminSite


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    verbose_name = "User Management"
    list_display = ("username", "email")
    list_display_links = ("username", "email")
    list_filter = ()
    search_fields = ("email", "username")
    ordering = ("-date_joined",)
    readonly_fields = ["last_login", "date_joined"]
    fieldsets = (
        (None, {"fields": ("username", "email")}),
        (_("Dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "username":
            field.help_text = None
        return field

    def save_model(self, request, obj, form, change):
        if not obj.is_staff:
            obj.is_staff = True
            obj.is_superuser = True
        super().save_model(request, obj, form, change)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "sku",
        "manufacturer_article_no",
        "gls_article_group_no",
        "sales_price",
        "is_blocked",
    )

    list_display_links = (
        "sku",
        "manufacturer_article_no",
        "name",
    )

    search_fields = (
        "sku",
        "manufacturer_article_no",
        "name",
        "manufacturer",
    )

    readonly_fields = ("manufacturer_name",)

    list_per_page = 50

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AdditionalMasterData)
class AdditionalMasterDataAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "article_no",
        "article_calculation_price",
        "active",
        "updated_at",
    )
    list_display_links = ("name", "article_no", "article_calculation_price", "active")
    search_fields = ("name", "article_no", "manufacturer_article_no")
    list_per_page = 50

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(BlockedProduct)
class BlockedProductAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "article_no",
        "manufacturer_article_no",
        "manufacturer",
        "updated_at",
    )
    list_display_links = (
        "name",
        "article_no",
        "manufacturer_article_no",
        "manufacturer",
    )
    search_fields = ("name", "article_no")
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 50

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ExportTask)
class ExportTaskAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "file_type",
        "status",
        "created_at",
        "completed_at",
        "download_link",
    )
    search_fields = ("name",)

    @admin.display(description="Download")
    def download_link(self, obj):
        if obj.download_url:
            return format_html(
                '<a href="{}" target="_blank" style="color:blue">Download</a>',
                obj.download_url,
            )

        return "-"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(MiddlewareSetting)
class MiddlewareSettingAdmin(admin.ModelAdmin):
    list_display = (
        "minimum_margin",
        "competitor_rule",
        "undercut_value",
        "updated_at",
    )
    list_display_links = (
        "minimum_margin",
        "competitor_rule",
        "undercut_value",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):

    list_display = (
        "source_with_colour",
        "level_with_colour",
        "message_with_colour",
        "created_at_with_colour",
    )
    list_display_links = (
        "source_with_colour",
        "level_with_colour",
        "message_with_colour",
    )
    search_fields = ("message",)
    ordering = ("-created_at",)
    list_per_page = 50

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def source_with_colour(self, obj):
        if obj.level == LogEntry.ERROR:
            return mark_safe(
                '<span style="color: #f1571a;">{}</span>'.format(obj.source)
            )
        return obj.source

    def level_with_colour(self, obj):
        if obj.level == LogEntry.ERROR:
            return mark_safe(
                '<span style="color: #f1571a;">{}</span>'.format(obj.level)
            )
        return obj.level

    def message_with_colour(self, obj):
        message_trunc = obj.message[:80] + ("..." if len(obj.message) > 80 else "")
        if obj.level == LogEntry.ERROR:
            return mark_safe(
                '<span style="color: #f1571a;">{}</span>'.format(message_trunc)
            )
        return message_trunc

    def created_at_with_colour(self, obj):
        if obj.level == LogEntry.ERROR:
            return mark_safe(
                '<span style="color: #f1571a;">{}</span>'.format(obj.created_at)
            )
        return obj.created_at

    source_with_colour.short_description = "Source"
    level_with_colour.short_description = "Level"
    message_with_colour.short_description = "Message"
    created_at_with_colour.short_description = "Created_at"


@admin.register(ProductPriceHistory)
class ProductPriceHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "product__name",
        "product__sku",
        "sales_price",
        "calculated_at",
    )
    search_fields = ("product__sku",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProductGtin)
class ProductGtinAdmin(admin.ModelAdmin):
    list_display = (
        "article_no",
        "sku",
        "gtin",
    )
    search_fields = ("article_no", "sku", "gtin")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
