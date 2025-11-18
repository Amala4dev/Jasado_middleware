from . import views
from django.urls import path


urlpatterns = [
    path("gls/", views.index, name="gls"),
    path(
        "export/master-data/",
        views.export_master_data,
        name="export_master_data",
    ),
]
