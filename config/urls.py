from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.contrib.staticfiles.views import serve
from home.views import logout_view

urlpatterns = [
    # Override admin logout to use our custom logout view
    path("admin/logout/", logout_view, name="admin_logout"),
    path("admin/", admin.site.urls),
    path("", include("home.urls")),
]

# Static file serving for DEVELOPMENT ONLY
# In production, use a dedicated web server (Nginx/Apache) or CDN
# This serves static files at /static/ (what Django receives after proxy strips /proxy/8000)
# Security: Only enabled when DEBUG=True to prevent use in production
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve),
    ]
