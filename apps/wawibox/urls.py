from . import views
from django.urls import path


urlpatterns = [
    path("wawi/", views.wawi, name="wawi"),
]
