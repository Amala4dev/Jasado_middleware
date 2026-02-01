from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("core/", include("apps.core.urls")),
    path("gls/", include("apps.gls.urls")),
    path("aera/", include("apps.aera.urls")),
    path("dentalheld/", include("apps.dentalheld.urls")),
    path("shopware/", include("apps.shopware.urls")),
    path("wawibox/", include("apps.wawibox.urls")),
    path("weclapp/", include("apps.weclapp.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
