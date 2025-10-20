from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/progress/', views.get_user_progress, name='get_progress'),
]
