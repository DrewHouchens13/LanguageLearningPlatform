"""
URL Configuration for Language Learning Platform.

This module defines the main URL routing for the Django application, including:
- Django admin interface at /admin/
- Home app routes (landing, login, dashboard, progress, etc.)
- Development-only static file serving (never used in production)

For production deployments, static files MUST be served by a dedicated web server
(e.g., Nginx, Apache) or CDN. Django's static file serving is inefficient and insecure
for production use.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.views import serve
from home.views import logout_view

urlpatterns = [
    # Override admin logout to use our custom logout view
    path("admin/logout/", logout_view, name="admin_logout"),
    path("admin/", admin.site.urls),
    path("", include("home.urls")),
]

# ============================================================================
# DEVELOPMENT STATIC FILE SERVING - DO NOT USE IN PRODUCTION
# ============================================================================
# WARNING: This is for development/testing ONLY. Never enable in production!
#
# In production, static files MUST be served by:
# - WhiteNoise (already configured in settings.py MIDDLEWARE)
# - Dedicated web server (Nginx/Apache)
# - CDN (Cloudflare, CloudFront, etc.)
#
# Django's serve() view is inefficient and can expose security vulnerabilities.
# The regex pattern is restricted to the static directory via Django's STATIC_URL.
#
# This section only runs when DEBUG=True (enforced by settings.py).
# ============================================================================
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve),
    ]
    # Serve media files in development (user uploaded content)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
