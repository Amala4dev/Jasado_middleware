from . import views
from django.urls import path


urlpatterns = [
    path("", views.index, name="gls"),
    path(
        "export/master-data/",
        views.export_master_data,
        name="export_master_data",
    ),
    path(
        "import/product-group/",
        views.upload_product_group,
        name="upload_product_group",
    ),
]
