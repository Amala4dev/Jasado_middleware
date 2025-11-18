from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("", include("apps.gls.urls")),
    path("", include("apps.aera.urls")),
    path("", include("apps.wawibox.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
