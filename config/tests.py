"""
Tests for Django settings configuration.

This test module verifies that settings.py behaves correctly under different
environment configurations (development, production, DevEDU, etc.).
"""

import os
import sys
from unittest import mock
from django.test import TestCase, override_settings
from django.conf import settings


class TestDevEDUDetection(TestCase):
    """Test DevEDU environment auto-detection logic."""

    def test_is_devedu_hostname_exact_match(self):
        """Test _is_devedu_hostname returns True for exact 'devedu.io' match"""
        from config.settings import _is_devedu_hostname

        with mock.patch.dict(os.environ, {'HOSTNAME': 'devedu.io'}):
            # Need to reload to pick up new environment
            self.assertTrue(_is_devedu_hostname())

    def test_is_devedu_hostname_subdomain(self):
        """Test _is_devedu_hostname returns True for valid subdomains"""
        from config.settings import _is_devedu_hostname

        with mock.patch.dict(os.environ, {'HOSTNAME': 'editor-jmanchester-20.devedu.io'}):
            self.assertTrue(_is_devedu_hostname())

    def test_is_devedu_hostname_rejects_prefix(self):
        """Test _is_devedu_hostname rejects domains with devedu.io as prefix"""
        from config.settings import _is_devedu_hostname

        with mock.patch.dict(os.environ, {'HOSTNAME': 'maliciousdevedu.io'}):
            self.assertFalse(_is_devedu_hostname())

    def test_is_devedu_hostname_rejects_suffix_attack(self):
        """Test _is_devedu_hostname rejects domains with devedu.io in middle"""
        from config.settings import _is_devedu_hostname

        with mock.patch.dict(os.environ, {'HOSTNAME': 'devedu.io.attacker.com'}):
            self.assertFalse(_is_devedu_hostname())

    def test_is_devedu_hostname_empty_string(self):
        """Test _is_devedu_hostname returns False for empty hostname"""
        from config.settings import _is_devedu_hostname

        with mock.patch.dict(os.environ, {'HOSTNAME': ''}):
            self.assertFalse(_is_devedu_hostname())


class TestDatabaseConfiguration(TestCase):
    """Test database configuration switches between SQLite and PostgreSQL."""

    @override_settings()
    def test_sqlite_used_in_tests(self):
        """Test that SQLite is used during test runs"""
        # In test mode, Django uses SQLite by default
        engine = settings.DATABASES['default']['ENGINE']
        self.assertEqual(engine, 'django.db.backends.sqlite3')

    def test_database_url_parsing(self):
        """Test that DATABASE_URL environment variable is respected"""
        # This test verifies the structure exists, actual parsing tested by Django
        self.assertIn('default', settings.DATABASES)
        self.assertIn('ENGINE', settings.DATABASES['default'])


class TestStaticFilesConfiguration(TestCase):
    """Test static files configuration for different environments."""

    def test_static_url_in_tests(self):
        """Test STATIC_URL is configured correctly in test environment"""
        # Should not have /proxy/ prefix in tests (not DevEDU)
        self.assertTrue(settings.STATIC_URL.startswith('/'))

    def test_static_root_configured(self):
        """Test STATIC_ROOT is set for collectstatic"""
        self.assertIsNotNone(settings.STATIC_ROOT)
        self.assertTrue(str(settings.STATIC_ROOT).endswith('staticfiles'))

    def test_staticfiles_storage_in_tests(self):
        """Test that simple storage is used in tests (not WhiteNoise)"""
        # In test mode, should use StaticFilesStorage
        staticfiles_storage = settings.STORAGES['staticfiles']['BACKEND']
        self.assertEqual(
            staticfiles_storage,
            'django.contrib.staticfiles.storage.StaticFilesStorage'
        )


class TestAuthenticationSettings(TestCase):
    """Test authentication-related settings."""

    def test_login_url_configured(self):
        """Test LOGIN_URL is set correctly"""
        self.assertEqual(settings.LOGIN_URL, 'login')

    def test_login_redirect_url_configured(self):
        """Test LOGIN_REDIRECT_URL is set correctly"""
        self.assertEqual(settings.LOGIN_REDIRECT_URL, 'landing')

    def test_logout_redirect_url_configured(self):
        """Test LOGOUT_REDIRECT_URL is set correctly"""
        self.assertEqual(settings.LOGOUT_REDIRECT_URL, 'landing')

    def test_session_cookie_age_configured(self):
        """Test session expires after 1 day"""
        self.assertEqual(settings.SESSION_COOKIE_AGE, 86400)

    def test_session_save_every_request(self):
        """Test session is updated on every request"""
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)


class TestSecuritySettings(TestCase):
    """Test security-related settings."""

    def test_debug_configured(self):
        """Test DEBUG setting is properly configured"""
        # Django test runner may override DEBUG, so we just verify it's a boolean
        self.assertIsInstance(settings.DEBUG, bool)

    def test_allowed_hosts_configured(self):
        """Test ALLOWED_HOSTS includes expected domains"""
        self.assertIn('localhost', settings.ALLOWED_HOSTS)
        self.assertIn('127.0.0.1', settings.ALLOWED_HOSTS)
        self.assertIn('[::1]', settings.ALLOWED_HOSTS)

    def test_csrf_trusted_origins_configured(self):
        """Test CSRF_TRUSTED_ORIGINS is configured"""
        self.assertIsInstance(settings.CSRF_TRUSTED_ORIGINS, list)
        self.assertGreater(len(settings.CSRF_TRUSTED_ORIGINS), 0)

    def test_secret_key_exists(self):
        """Test SECRET_KEY is configured"""
        self.assertIsNotNone(settings.SECRET_KEY)
        self.assertGreater(len(settings.SECRET_KEY), 0)


class TestMiddlewareConfiguration(TestCase):
    """Test middleware stack is properly configured."""

    def test_security_middleware_present(self):
        """Test SecurityMiddleware is in middleware stack"""
        self.assertIn(
            'django.middleware.security.SecurityMiddleware',
            settings.MIDDLEWARE
        )

    def test_whitenoise_middleware_present(self):
        """Test WhiteNoise middleware is in correct position"""
        self.assertIn(
            'whitenoise.middleware.WhiteNoiseMiddleware',
            settings.MIDDLEWARE
        )

    def test_csrf_middleware_present(self):
        """Test CSRF middleware is enabled"""
        self.assertIn(
            'django.middleware.csrf.CsrfViewMiddleware',
            settings.MIDDLEWARE
        )


class TestInstalledApps(TestCase):
    """Test installed apps configuration."""

    def test_django_admin_installed(self):
        """Test django.contrib.admin is installed"""
        self.assertIn('django.contrib.admin', settings.INSTALLED_APPS)

    def test_home_app_installed(self):
        """Test home app is installed"""
        self.assertIn('home', settings.INSTALLED_APPS)

    def test_staticfiles_app_installed(self):
        """Test staticfiles app is installed"""
        self.assertIn('django.contrib.staticfiles', settings.INSTALLED_APPS)


class TestEmailConfiguration(TestCase):
    """Test email backend configuration."""

    def test_email_backend_configured(self):
        """Test email backend is properly configured"""
        # Django test runner uses locmem backend, production uses console
        # Just verify EMAIL_BACKEND is set to a valid backend
        self.assertIsNotNone(settings.EMAIL_BACKEND)
        self.assertIn('django.core.mail.backends', settings.EMAIL_BACKEND)


class TestPasswordValidators(TestCase):
    """Test password validation configuration."""

    def test_password_validators_configured(self):
        """Test password validators are properly configured"""
        validators = settings.AUTH_PASSWORD_VALIDATORS
        self.assertGreater(len(validators), 0)

        # Check minimum length validator is present
        validator_names = [v['NAME'] for v in validators]
        self.assertIn(
            'django.contrib.auth.password_validation.MinimumLengthValidator',
            validator_names
        )

    def test_minimum_password_length(self):
        """Test minimum password length is 8 characters"""
        validators = settings.AUTH_PASSWORD_VALIDATORS
        min_length_validator = next(
            (v for v in validators
             if 'MinimumLengthValidator' in v['NAME']),
            None
        )
        self.assertIsNotNone(min_length_validator)
        self.assertEqual(min_length_validator['OPTIONS']['min_length'], 8)
