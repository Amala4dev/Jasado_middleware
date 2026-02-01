from . import views
from django.urls import path


urlpatterns = [
    path("", views.index, name="weclapp"),
    path(
        "webhook/9f3c2d7e-6a4f-4e1a-b6b4-8c0e9c3a91f2/",
        views.purchase_order_webhook,
        name="purchase_order_webhook",
    ),
]
