"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("authentication.urls")),
    path("", include("common.urls")),
    path("", include("training.urls")),
    path("", include("duty.urls")),
]

handler400 = "authentication.error_views.bad_request"
handler403 = "authentication.error_views.permission_denied"
handler404 = "authentication.error_views.page_not_found"
handler500 = "authentication.error_views.server_error"

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
