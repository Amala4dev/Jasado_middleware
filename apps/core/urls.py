from . import views
from django.urls import path


urlpatterns = [
    path(
        "import/additional-products/",
        views.upload_additional_products,
        name="upload_additional_products",
    ),
    path(
        "import/blocked-products/",
        views.upload_blocked_products,
        name="upload_blocked_products",
    ),
    path(
        "import/product-gtin/",
        views.upload_product_gtin,
        name="upload_product_gtin",
    ),
    path(
        "export/amazon-data/",
        views.export_amazon_data,
        name="export_amazon_data",
    ),
    path(
        "export/kaufland-data/",
        views.export_kaufland_data,
        name="export_kaufland_data",
    ),
    path(
        "export/",
        views.process_pending_exports,
        name="process_pending_exports",
    ),
    path(
        "download-file/",
        views.download_file,
        name="download_file",
    ),
    path(
        "run/",
        views.run_automations,
        name="run_automations",
    ),
    path(
        "core/",
        views.core,
        name="core",
    ),
]
