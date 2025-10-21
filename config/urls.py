from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.contrib.staticfiles.views import serve
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include(("home.urls", "home"), namespace="home")),
    path("dashboard/", include(("dashboard.urls", "dashboard"), namespace="dashboard")),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
]

# In development, serve static files at /static/ (what Django receives after proxy strips /proxy/8000)
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve),
    ]
