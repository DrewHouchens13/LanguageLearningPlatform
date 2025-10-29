from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse, resolve
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from enum import Enum
from unittest.mock import patch

from home.models import UserProgress, LessonCompletion, QuizResult
from .test_utils import create_test_user, create_test_superuser, AdminTestCase

from home.views import forgot_password_view, reset_password_view, forgot_username_view


# ============================================================================
# PASSWORD RECOVERY TESTS
# ============================================================================

class ForgotPasswordTests(TestCase):
    """Tests for forgot password functionality"""

    def setUp(self):
        """Create test user for each test"""
        self.client = Client()
        self.user = create_test_user(email='user@example.com')

    def test_forgot_password_page_loads(self):
        """Test forgot password page loads successfully"""
        response = self.client.get(reverse('forgot_password'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forgot Password?')
        self.assertContains(response, 'Send Reset Link')

    def test_forgot_password_sends_email_for_existing_user(self):
        """Test password reset email is sent for existing user"""
        from django.core import mail

        response = self.client.post(reverse('forgot_password'), {
            'email': self.user.email
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'password reset link has been sent')

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn('Password Reset', mail.outbox[0].subject)
        self.assertIn('reset-password', mail.outbox[0].body)

    def test_forgot_password_no_email_for_nonexistent_user(self):
        """Test no email sent for non-existent user but same message shown"""
        from django.core import mail

        response = self.client.post(reverse('forgot_password'), {
            'email': 'nonexistent@example.com'
        })

        # Should show same success message (security - don't reveal if user exists)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'password reset link has been sent')

        # But no email should be sent
        self.assertEqual(len(mail.outbox), 0)

    def test_forgot_password_form_stays_visible(self):
        """Test form remains visible after submission for retry"""
        response = self.client.post(reverse('forgot_password'), {
            'email': 'test@example.com'
        })

        # Form should still be visible
        self.assertContains(response, 'Email Address')
        self.assertContains(response, 'Send Reset Link')

class ResetPasswordTests(TestCase):
    """Tests for password reset with token"""

    def setUp(self):
        """Create test user and generate reset token"""
        self.client = Client()
        self.user = create_test_user(email='user@example.com')

        # Generate valid token
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        self.token = default_token_generator.make_token(self.user)
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))

    def test_reset_password_page_loads_with_valid_token(self):
        """Test reset password page loads with valid token"""
        url = reverse('reset_password', kwargs={
            'uidb64': self.uid,
            'token': self.token
        })

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reset Your Password')
        self.assertContains(response, 'New Password')

    def test_reset_password_invalid_token(self):
        """Test reset password page shows error with invalid token"""
        url = reverse('reset_password', kwargs={
            'uidb64': self.uid,
            'token': 'invalid-token'
        })

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'invalid or has expired')

    def test_reset_password_success(self):
        """Test successful password reset"""
        url = reverse('reset_password', kwargs={
            'uidb64': self.uid,
            'token': self.token
        })

        new_password = 'NewSecurePassword123!'
        response = self.client.post(url, {
            'new_password': new_password,
            'confirm_password': new_password
        })

        # Should redirect to landing page
        self.assertEqual(response.status_code, 302)

        # Password should be updated
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

        # User should be logged in
        self.assertIn('_auth_user_id', self.client.session)

    def test_reset_password_mismatch(self):
        """Test password reset fails when passwords don't match"""
        url = reverse('reset_password', kwargs={
            'uidb64': self.uid,
            'token': self.token
        })

        response = self.client.post(url, {
            'new_password': 'Password123!',
            'confirm_password': 'DifferentPassword123!'
        })

        self.assertContains(response, 'Passwords do not match')

    def test_reset_password_too_short(self):
        """Test password reset fails with short password"""
        url = reverse('reset_password', kwargs={
            'uidb64': self.uid,
            'token': self.token
        })

        response = self.client.post(url, {
            'new_password': 'short',
            'confirm_password': 'short'
        })

        self.assertContains(response, 'at least 8 characters')

class ForgotUsernameTests(TestCase):
    """Tests for forgot username functionality"""

    def setUp(self):
        """Create test user for each test"""
        self.client = Client()
        self.user = create_test_user(
            username='testuser',
            email='user@example.com'
        )

    def test_forgot_username_page_loads(self):
        """Test forgot username page loads successfully"""
        response = self.client.get(reverse('forgot_username'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forgot Username?')
        self.assertContains(response, 'Send Username')

    def test_forgot_username_sends_email_for_existing_user(self):
        """Test username reminder email is sent for existing user"""
        from django.core import mail

        response = self.client.post(reverse('forgot_username'), {
            'email': self.user.email
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'username reminder has been sent')

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn('Username Reminder', mail.outbox[0].subject)
        self.assertIn(self.user.username, mail.outbox[0].body)

    def test_forgot_username_no_email_for_nonexistent_user(self):
        """Test no email sent for non-existent user but same message shown"""
        from django.core import mail

        response = self.client.post(reverse('forgot_username'), {
            'email': 'nonexistent@example.com'
        })

        # Should show same success message (security)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'username reminder has been sent')

        # But no email should be sent
        self.assertEqual(len(mail.outbox), 0)

    def test_forgot_username_form_stays_visible(self):
        """Test form remains visible after submission for retry"""
        response = self.client.post(reverse('forgot_username'), {
            'email': 'test@example.com'
        })

        # Form should still be visible
        self.assertContains(response, 'Email Address')
        self.assertContains(response, 'Send Username')

