"""config URL Configuration"""

from django.contrib import admin
from django.urls import path, include, register_converter
from django.conf import settings
from django.conf.urls.static import static

from weather.converters import FloatConverter

register_converter(FloatConverter, "float")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("weather.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
