"""
Django app configuration for the home application.
"""
from django.apps import AppConfig


class HomeConfig(AppConfig):
    """Configuration for the home (main) application."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'home'
