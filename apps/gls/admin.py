from django.contrib import admin
from .models import *


@admin.register(GLSMasterData)
class GLSMasterDataAdmin(admin.ModelAdmin):
    list_display = (
        "article_no",
        "description",
        "manufacturer_name",
        "article_group_no",
        "article_group_name",
        "product_group_no",
        "product_group_name",
        "blocked",
        "freely_available",
    )
    list_display_links = ("article_no", "description")
    search_fields = ("article_no", "description", "manufacturer_article_no")
    readonly_fields = (
        "article_group_name",
        "product_group_name",
        "manufacturer_name",
    )

    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "article_no",
                    "description",
                    "created_on",
                    "last_fetch_from_gls",
                )
            },
        ),
        (
            "Manufacturer Details",
            {
                "fields": (
                    "manufacturer",
                    "manufacturer_article_no",
                    "manufacturer_name",
                )
            },
        ),
        (
            "Article Group & Product Group",
            {
                "fields": (
                    "article_group_no",
                    "article_group_name",
                    "product_group_no",
                    "product_group_name",
                )
            },
        ),
        (
            "Identifiers & Packaging",
            {
                "fields": (
                    "abc_license_plate",
                    "packaging_unit",
                    "alternative_article_no",
                    "package_contents",
                    "packing_unit",
                )
            },
        ),
        (
            "Customs & Origin",
            {
                "fields": (
                    "customs_position",
                    "country_of_origin",
                    "country_of_origin_alt",
                    "vat_rate",
                )
            },
        ),
        (
            "Medical / Pharmaceutical",
            {
                "fields": (
                    "medical_device",
                    "drug",
                    "pzn_no",
                    "batch_number_required",
                    "serial_number_required",
                    "mhd_compulsory",
                )
            },
        ),
        (
            "Logistics & Delivery",
            {
                "fields": (
                    "avg_delivery_time",
                    "order_suggestion",
                    "warehouse",
                    "freely_available",
                    "blocked",
                )
            },
        ),
        (
            "Hazard & Safety Information",
            {
                "fields": (
                    "un_number",
                    "hazard_code",
                    "dangerous_goods",
                    "store_refrigerated",
                )
            },
        ),
        (
            "Dimensions & Weight",
            {
                "fields": (
                    "length",
                    "width",
                    "height",
                    "weight",
                )
            },
        ),
        (
            "HIBC Information",
            {
                "fields": (
                    "hibc_manufacturer_id",
                    "hibc_article_no",
                    "hibc_packaging_index",
                )
            },
        ),
    )

    def has_add_permission(self, r, o=None):
        return False

    def has_change_permission(self, r, o=None):
        return False

    def has_delete_permission(self, r, o=None):
        return False


@admin.register(GLSStockLevel)
class GLSStockLevelAdmin(admin.ModelAdmin):
    list_display = (
        "article_no",
        "inventory",
        "ordered_qty",
        "next_receipt_date",
        "last_fetch_from_gls",
    )
    search_fields = ("article_no",)

    def has_add_permission(self, r, o=None):
        return False

    def has_change_permission(self, r, o=None):
        return False

    def has_delete_permission(self, r, o=None):
        return False


@admin.register(GLSPriceList)
class GLSPriceListAdmin(admin.ModelAdmin):
    list_display = (
        "article_no",
        "purchase_price",
        "bill_back_price",
        "recommended_retail_price",
        "last_fetch_from_gls",
    )
    search_fields = ("article_no",)

    def has_add_permission(self, r, o=None):
        return False

    def has_change_permission(self, r, o=None):
        return False

    def has_delete_permission(self, r, o=None):
        return False


@admin.register(GLSPromotionHeader)
class GLSPromotionHeaderAdmin(admin.ModelAdmin):
    list_display = (
        "action_code",
        "short_text",
        "valid_from",
        "valid_to",
        "customer_number",
        "last_fetch_from_gls",
    )
    search_fields = ("action_code", "short_text")

    def has_add_permission(self, r, o=None):
        return False

    def has_change_permission(self, r, o=None):
        return False

    def has_delete_permission(self, r, o=None):
        return False


@admin.register(GLSPromotionPosition)
class GLSPromotionPositionAdmin(admin.ModelAdmin):
    list_display = (
        "action_code",
        "article_no",
        "position_number",
        "set_qty",
        "last_fetch_from_gls",
    )
    search_fields = ("action_code", "article_no")

    def has_add_permission(self, r, o=None):
        return False

    def has_change_permission(self, r, o=None):
        return False

    def has_delete_permission(self, r, o=None):
        return False


@admin.register(GLSPromotionPrice)
class GLSPromotionPriceAdmin(admin.ModelAdmin):
    list_display = (
        "article_no",
        "action_code",
        "promotion_price",
        "valid_from",
        "valid_to",
        "last_fetch_from_gls",
    )
    search_fields = ("article_no", "action_code")

    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "product",
                    "article_no",
                    "action_code",
                    "origin_code",
                    "change_flag",
                    "last_fetch_from_gls",
                )
            },
        ),
        (
            "Promotion Duration",
            {
                "fields": (
                    "valid_from",
                    "valid_to",
                )
            },
        ),
        (
            "Promotion Pricing",
            {
                "fields": (
                    "promotion_price",
                    "promotional_purchase_price",
                    "net_gross_flag",
                )
            },
        ),
        (
            "Quantity Tiers",
            {
                "fields": (
                    "qty_tier_1",
                    "qty_tier_2",
                    "qty_tier_3",
                    "qty_tier_4",
                    "qty_tier_5",
                )
            },
        ),
        (
            "Tier Prices",
            {
                "fields": (
                    "price_tier_1",
                    "price_tier_2",
                    "price_tier_3",
                    "price_tier_4",
                    "price_tier_5",
                )
            },
        ),
    )

    def has_add_permission(self, r, o=None):
        return False

    def has_change_permission(self, r, o=None):
        return False

    def has_delete_permission(self, r, o=None):
        return False


@admin.register(GLSSupplier)
class GLSSupplierAdmin(admin.ModelAdmin):
    list_display = ("supplier_no", "name1", "country", "city", "blocked", "drug_ban")
    search_fields = ("supplier_no", "name1", "city")

    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "supplier_no",
                    "name1",
                    "name2",
                    "search_term",
                )
            },
        ),
        (
            "Address",
            {
                "fields": (
                    "street",
                    "postal_code",
                    "city",
                    "country",
                )
            },
        ),
        (
            "Contact Details",
            {
                "fields": (
                    "phone",
                    "fax",
                    "email",
                    "url",
                )
            },
        ),
        (
            "Legal & Compliance",
            {
                "fields": (
                    "vat_id",
                    "packaging_reg_no",
                    "blocked",
                    "drug_ban",
                )
            },
        ),
    )

    def has_add_permission(self, r, o=None):
        return False

    def has_change_permission(self, r, o=None):
        return False

    def has_delete_permission(self, r, o=None):
        return False


@admin.register(GLSOrderConfirmation)
class GLSOrderConfirmationAdmin(admin.ModelAdmin):

    list_display = (
        "record_type",
        "order_number",
        "article_no",
        "position",
        "actual_value",
        "ordered_qty",
        "expected_delivery_date",
    )

    search_fields = ("order_number", "article_no")

    fieldsets = (
        (
            "Order Information",
            {
                "fields": (
                    "order_number",
                    "position",
                    "record_type",
                    "order_method",
                    "document_number",
                    "internal_user",
                    "processed",
                    "last_fetch_from_gls",
                )
            },
        ),
        (
            "Article Details",
            {
                "fields": (
                    "article_no",
                    "unit_price",
                    "ordered_qty",
                    "actual_value",
                    "info",
                    "backorder_text",
                )
            },
        ),
        (
            "Customer Details",
            {
                "fields": (
                    "customer_number",
                    "end_customer_id",
                )
            },
        ),
        (
            "Delivery & Dates",
            {
                "fields": (
                    "expected_delivery_date",
                    "goods_receipt_date",
                    "delivery_note_date",
                    "packing_time",
                    "shipping_info",
                )
            },
        ),
        ("Control & Info", {"fields": ("control_number",)}),
    )

    def has_add_permission(self, r, o=None):
        return False

    def has_change_permission(self, r, o=None):
        return False

    def has_delete_permission(self, r, o=None):
        return False


@admin.register(GLSBackorder)
class GLSBackorderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "article_no",
        "backorder_qty",
        "next_goods_receipt",
        "confirmed_delivery_date",
        "last_fetch_from_gls",
    )
    search_fields = ("order_number", "article_no")

    def has_add_permission(self, r, o=None):
        return False

    def has_change_permission(self, r, o=None):
        return False

    def has_delete_permission(self, r, o=None):
        return False


# class GLSOrderLineInline(admin.TabularInline):
#     model = GLSOrderLine
#     extra = 0
#     can_delete = False
#     show_change_link = True
#     readonly_fields = [f.name for f in GLSOrderLine._meta.fields]


# @admin.register(GLSOrderHeader)
# class GLSOrderHeaderAdmin(admin.ModelAdmin):
#     list_display = (
#         "order_number",
#         "branch_no",
#         "customer_id",
#         "delivery_date",
#         "is_processed",
#     )
#     search_fields = ("order_number", "customer_id")
#     list_filter = ("is_processed",)
#     inlines = [GLSOrderLineInline]

#     def has_add_permission(self, r, o=None):
#         return False

#     def has_change_permission(self, r, o=None):
#         return False

#     def has_delete_permission(self, r, o=None):
#         return False


# @admin.register(GLSOrderLine)
# class GLSOrderLineAdmin(admin.ModelAdmin):
#     list_display = ("order_number", "gls_article_no", "qty", "unit_price", "free_item")
#     search_fields = ("order_number", "gls_article_no")

#     def has_add_permission(self, r, o=None):
#         return False

#     def has_change_permission(self, r, o=None):
#         return False

#     def has_delete_permission(self, r, o=None):
#         return False


@admin.register(GLSOrderStatus)
class GLSOrderStatusAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "position",
        "delivered",
        "ordered_qty",
        "document_number",
        "delivered_qty",
        "status_info",
        "last_updated",
    )
    search_fields = ("order_number", "position", "status_info")
    list_filter = ("delivered", "admin_notified")

    fieldsets = (
        (
            "Order Information",
            {
                "fields": (
                    "order_number",
                    "position",
                    "article_no",
                    "status_info",
                    "backorder_text",
                    "admin_notified",
                )
            },
        ),
        (
            "Quantities",
            {
                "fields": (
                    "ordered_qty",
                    "delivered_qty",
                    "planned_qty",
                    "last_sent_qty",
                )
            },
        ),
        (
            "Package & Delivery",
            {
                "fields": (
                    "package_type",
                    "number_of_package",
                    "package_number",
                    "pack_time",
                    "pack_date",
                    "expected_delivery_date",
                    "delivery_date",
                    "planned_goods_receipt_date",
                    "shipping_service",
                )
            },
        ),
        (
            "Identifiers",
            {
                "fields": (
                    "control_number",
                    "serial_number",
                    "batch_number",
                    "siemens_process_no",
                    "dfu_number",
                    "expiry_date",
                )
            },
        ),
        (
            "Customer Details",
            {
                "fields": (
                    "customer_number",
                    "end_customer_id",
                    "unit_price",
                    "internal_user",
                    "document_number",
                )
            },
        ),
        (
            "Date",
            {"fields": ("last_updated",)},
        ),
    )

    def has_add_permission(self, r, o=None):
        return False

    def has_change_permission(self, r, o=None):
        return False

    def has_delete_permission(self, r, o=None):
        return False
