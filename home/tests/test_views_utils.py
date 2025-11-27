"""
Tests for home/views_utils.py utilities.

Tests cover:
- block_if_onboarding_completed decorator
- get_client_ip function (proxy handling, validation)
- check_rate_limit function
- send_template_email function
"""

from unittest.mock import MagicMock, patch, PropertyMock
from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import ImproperlyConfigured

from home.views_utils import (
    block_if_onboarding_completed,
    get_client_ip,
    check_rate_limit,
    send_template_email,
)
from home.models import OnboardingAttempt


class BlockIfOnboardingCompletedTests(TestCase):
    """Tests for the block_if_onboarding_completed decorator."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_decorator_allows_request_without_session(self):
        """Decorator should allow requests without onboarding session."""
        @block_if_onboarding_completed
        def dummy_view(request):
            return 'success'

        request = self.factory.get('/test/')
        request.session = SessionStore()

        result = dummy_view(request)
        self.assertEqual(result, 'success')

    def test_decorator_clears_completed_attempt(self):
        """Decorator should clear session if attempt is completed."""
        from django.utils import timezone

        @block_if_onboarding_completed
        def dummy_view(request):
            return 'success'

        # Create a completed attempt
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        attempt.completed_at = timezone.now()
        attempt.save()

        request = self.factory.get('/test/')
        request.session = SessionStore()
        request.session['onboarding_attempt_id'] = attempt.id
        request.session.save()

        result = dummy_view(request)
        self.assertEqual(result, 'success')
        # Session should be cleared
        self.assertIsNone(request.session.get('onboarding_attempt_id'))

    def test_decorator_clears_nonexistent_attempt(self):
        """Decorator should clear session if attempt doesn't exist."""
        @block_if_onboarding_completed
        def dummy_view(request):
            return 'success'

        request = self.factory.get('/test/')
        request.session = SessionStore()
        request.session['onboarding_attempt_id'] = 99999  # Non-existent
        request.session.save()

        result = dummy_view(request)
        self.assertEqual(result, 'success')
        self.assertIsNone(request.session.get('onboarding_attempt_id'))

    def test_decorator_keeps_incomplete_attempt(self):
        """Decorator should keep session for incomplete attempts."""
        @block_if_onboarding_completed
        def dummy_view(request):
            return 'success'

        # Create an incomplete attempt
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )

        request = self.factory.get('/test/')
        request.session = SessionStore()
        request.session['onboarding_attempt_id'] = attempt.id
        request.session.save()

        result = dummy_view(request)
        self.assertEqual(result, 'success')
        # Session should be preserved
        self.assertEqual(request.session.get('onboarding_attempt_id'), attempt.id)


class GetClientIPTests(TestCase):
    """Tests for the get_client_ip function."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()

    @override_settings(TRUST_X_FORWARDED_FOR='always')
    def test_returns_xff_header_when_trusted(self):
        """Should return X-Forwarded-For IP when trusted."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1, 10.0.0.1'
        request.META['REMOTE_ADDR'] = '10.0.0.1'

        ip = get_client_ip(request)
        self.assertEqual(ip, '203.0.113.1')

    @override_settings(TRUST_X_FORWARDED_FOR='never')
    def test_returns_remote_addr_when_xff_not_trusted(self):
        """Should return REMOTE_ADDR when X-Forwarded-For not trusted."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1'
        request.META['REMOTE_ADDR'] = '192.168.1.1'

        ip = get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')

    @override_settings(TRUST_X_FORWARDED_FOR='debug', DEBUG=True)
    def test_trusts_xff_in_debug_mode(self):
        """Should trust X-Forwarded-For in DEBUG mode with 'debug' setting."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1'
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        ip = get_client_ip(request)
        self.assertEqual(ip, '203.0.113.1')

    @override_settings(TRUST_X_FORWARDED_FOR='debug', DEBUG=False)
    def test_does_not_trust_xff_when_not_debug(self):
        """Should not trust X-Forwarded-For when not in DEBUG mode."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1'
        request.META['REMOTE_ADDR'] = '192.168.1.1'

        ip = get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')

    def test_returns_remote_addr_without_xff(self):
        """Should return REMOTE_ADDR when no X-Forwarded-For header."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.100'

        ip = get_client_ip(request)
        self.assertEqual(ip, '192.168.1.100')

    def test_returns_unknown_when_no_addr(self):
        """Should return 'unknown' when no address available."""
        request = self.factory.get('/')
        request.META.pop('REMOTE_ADDR', None)

        ip = get_client_ip(request)
        self.assertEqual(ip, 'unknown')

    @override_settings(TRUST_X_FORWARDED_FOR='always')
    def test_handles_invalid_xff_ip(self):
        """Should fall back to REMOTE_ADDR for invalid X-Forwarded-For IP."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = 'not-an-ip'
        request.META['REMOTE_ADDR'] = '192.168.1.1'

        ip = get_client_ip(request)
        self.assertEqual(ip, '192.168.1.1')

    def test_handles_invalid_remote_addr(self):
        """Should return 'unknown' for invalid REMOTE_ADDR."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = 'invalid-ip'

        ip = get_client_ip(request)
        self.assertEqual(ip, 'unknown')

    @override_settings(TRUST_X_FORWARDED_FOR='invalid_value', DEBUG=True)
    def test_warns_on_invalid_setting_in_debug(self):
        """Should warn and default to debug mode for invalid setting in DEBUG."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1'
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        ip = get_client_ip(request)
        # In DEBUG mode with invalid setting, should trust XFF
        self.assertEqual(ip, '203.0.113.1')

    @override_settings(TRUST_X_FORWARDED_FOR='invalid_value', DEBUG=False)
    def test_raises_on_invalid_setting_in_production(self):
        """Should raise ImproperlyConfigured for invalid setting in production."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '203.0.113.1'
        request.META['REMOTE_ADDR'] = '127.0.0.1'

        with self.assertRaises(ImproperlyConfigured):
            get_client_ip(request)

    @override_settings(TRUST_X_FORWARDED_FOR='always')
    def test_handles_ipv6_address(self):
        """Should handle valid IPv6 addresses."""
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '2001:db8::1'
        request.META['REMOTE_ADDR'] = '::1'

        ip = get_client_ip(request)
        self.assertEqual(ip, '2001:db8::1')


class CheckRateLimitTests(TestCase):
    """Tests for the check_rate_limit function."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    })
    def test_allows_first_request(self):
        """Should allow the first request."""
        from django.core.cache import cache
        cache.clear()

        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'

        is_allowed, remaining, retry_after = check_rate_limit(
            request, 'test_action', limit=5, period=300
        )

        self.assertTrue(is_allowed)
        self.assertEqual(remaining, 4)
        self.assertEqual(retry_after, 0)

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    })
    def test_decrements_remaining_attempts(self):
        """Should decrement remaining attempts."""
        from django.core.cache import cache
        cache.clear()

        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.2'

        # Make several requests and verify remaining decrements
        # First call: remaining = limit - 0 - 1 = 4
        # Second call: remaining = limit - 1 - 1 = 3
        # Third call: remaining = limit - 2 - 1 = 2
        expected_remaining = [4, 3, 2]
        for i in range(3):
            is_allowed, remaining, _ = check_rate_limit(
                request, 'test_action2', limit=5, period=300
            )
            self.assertTrue(is_allowed)
            self.assertEqual(remaining, expected_remaining[i])

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    })
    def test_blocks_after_limit_exceeded(self):
        """Should block requests after limit is exceeded."""
        from django.core.cache import cache
        cache.clear()

        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.3'

        # Exhaust the limit
        for _ in range(5):
            check_rate_limit(request, 'test_action3', limit=5, period=300)

        # Next request should be blocked
        is_allowed, remaining, retry_after = check_rate_limit(
            request, 'test_action3', limit=5, period=300
        )

        self.assertFalse(is_allowed)
        self.assertEqual(remaining, 0)
        self.assertGreater(retry_after, 0)

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    })
    def test_different_actions_have_separate_limits(self):
        """Different actions should have separate rate limits."""
        from django.core.cache import cache
        cache.clear()

        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.4'

        # Exhaust limit for action1
        for _ in range(5):
            check_rate_limit(request, 'action1', limit=5, period=300)

        # action2 should still be allowed
        is_allowed, _, _ = check_rate_limit(request, 'action2', limit=5, period=300)
        self.assertTrue(is_allowed)

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    })
    def test_different_ips_have_separate_limits(self):
        """Different IPs should have separate rate limits."""
        from django.core.cache import cache
        cache.clear()

        request1 = self.factory.get('/')
        request1.META['REMOTE_ADDR'] = '192.168.1.5'

        request2 = self.factory.get('/')
        request2.META['REMOTE_ADDR'] = '192.168.1.6'

        # Exhaust limit for IP1
        for _ in range(5):
            check_rate_limit(request1, 'shared_action', limit=5, period=300)

        # IP2 should still be allowed
        is_allowed, _, _ = check_rate_limit(request2, 'shared_action', limit=5, period=300)
        self.assertTrue(is_allowed)


class SendTemplateEmailTests(TestCase):
    """Tests for the send_template_email function."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @override_settings(DEFAULT_FROM_EMAIL='noreply@example.com')
    @patch('django.core.mail.send_mail')
    def test_sends_email_successfully(self, mock_send_mail):
        """Should send email successfully."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'

        result = send_template_email(
            request,
            'emails/password_reset_email.txt',
            context={'user': self.user, 'reset_url': 'http://example.com/reset'},
            subject='Test Subject',
            recipient_email='recipient@example.com',
            log_prefix='Test email'
        )

        self.assertTrue(result)
        mock_send_mail.assert_called_once()

    @override_settings(DEFAULT_FROM_EMAIL='noreply@example.com')
    @patch('django.core.mail.send_mail')
    def test_returns_false_for_invalid_email(self, mock_send_mail):
        """Should return False for invalid email format."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'

        result = send_template_email(
            request,
            'emails/password_reset_email.txt',
            context={'user': self.user, 'reset_url': 'http://example.com/reset'},
            subject='Test Subject',
            recipient_email='not-an-email',
            log_prefix='Test email'
        )

        self.assertFalse(result)
        mock_send_mail.assert_not_called()

    def test_raises_for_missing_from_email(self):
        """Should raise ImproperlyConfigured if DEFAULT_FROM_EMAIL not set."""
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'

        with override_settings(DEFAULT_FROM_EMAIL=None):
            with self.assertRaises(ImproperlyConfigured):
                send_template_email(
                    request,
                    'emails/password_reset_email.txt',
                    context={'user': self.user, 'reset_url': 'http://example.com/reset'},
                    subject='Test Subject',
                    recipient_email='recipient@example.com',
                    log_prefix='Test email'
                )

    @override_settings(DEFAULT_FROM_EMAIL='noreply@example.com')
    @patch('django.core.mail.send_mail')
    def test_retries_on_smtp_error(self, mock_send_mail):
        """Should retry on SMTP errors with exponential backoff."""
        from smtplib import SMTPException

        # Fail twice, then succeed
        mock_send_mail.side_effect = [SMTPException('Error'), SMTPException('Error'), None]

        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'

        with patch('time.sleep'):  # Don't actually wait
            result = send_template_email(
                request,
                'emails/password_reset_email.txt',
                context={'user': self.user, 'reset_url': 'http://example.com/reset'},
                subject='Test Subject',
                recipient_email='recipient@example.com',
                log_prefix='Test email',
                max_retries=3
            )

        self.assertTrue(result)
        self.assertEqual(mock_send_mail.call_count, 3)

    @override_settings(DEFAULT_FROM_EMAIL='noreply@example.com')
    @patch('django.core.mail.send_mail')
    def test_returns_false_after_max_retries(self, mock_send_mail):
        """Should return False after exhausting retries."""
        from smtplib import SMTPException

        mock_send_mail.side_effect = SMTPException('Persistent error')

        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'

        with patch('time.sleep'):
            result = send_template_email(
                request,
                'emails/password_reset_email.txt',
                context={'user': self.user, 'reset_url': 'http://example.com/reset'},
                subject='Test Subject',
                recipient_email='recipient@example.com',
                log_prefix='Test email',
                max_retries=3
            )

        self.assertFalse(result)
        self.assertEqual(mock_send_mail.call_count, 3)

    @override_settings(DEFAULT_FROM_EMAIL='noreply@example.com')
    @patch('django.core.mail.send_mail')
    def test_handles_bad_header_error(self, mock_send_mail):
        """Should handle BadHeaderError."""
        from django.core.mail import BadHeaderError

        mock_send_mail.side_effect = BadHeaderError('Invalid header')

        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'

        with patch('time.sleep'):
            result = send_template_email(
                request,
                'emails/password_reset_email.txt',
                context={'user': self.user, 'reset_url': 'http://example.com/reset'},
                subject='Test Subject',
                recipient_email='recipient@example.com',
                log_prefix='Test email',
                max_retries=1
            )

        self.assertFalse(result)
