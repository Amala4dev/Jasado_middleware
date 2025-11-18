from . import views
from django.urls import path


urlpatterns = [
    path('aera/', views.index, name='aera'),
]
