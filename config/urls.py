from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.contrib.staticfiles.views import serve
from home.views import logout_view

urlpatterns = [
    # Override admin logout to use our custom logout view
    # This ensures consistent behavior with the main logout button
    path("admin/logout/", logout_view, name="admin_logout"),
    path("admin/", admin.site.urls),
    path("", include("home.urls")),
]

# In development, serve static files at /static/ (what Django receives after proxy strips /proxy/8000)
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve),
    ]
