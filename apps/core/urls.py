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
]
