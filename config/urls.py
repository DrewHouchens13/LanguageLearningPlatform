from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.contrib.staticfiles.views import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("home.urls")),
]

# In development, serve static files at /static/ (what Django receives after proxy strips /proxy/8000)
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve),
    ]
