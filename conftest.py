"""Pytest configuration for Django tests"""
import pytest
from django.conf import settings


@pytest.fixture(scope='session', autouse=True)
def django_test_settings():
    """Configure Django settings for tests"""
    # Disable APPEND_SLASH to avoid 301 redirects in tests
    settings.APPEND_SLASH = False

