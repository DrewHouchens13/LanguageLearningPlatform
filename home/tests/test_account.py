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

from home.views import account_view


# ============================================================================
# ACCOUNT MANAGEMENT TESTS
# ============================================================================

class AccountAction(str, Enum):
    """
    Enum for account management action types.

    Using an Enum provides:
    - Type safety and autocomplete in IDEs
    - Clear namespace for related constants
    - Prevention of typos in test code
    - Self-documenting code
    """
    UPDATE_EMAIL = 'update_email'
    UPDATE_NAME = 'update_name'
    UPDATE_USERNAME = 'update_username'
    UPDATE_PASSWORD = 'update_password'

class AccountViewTests(TestCase):
    """
    Tests for the account management page.

    Note: These tests modify the user object (email, name, username, password),
    so we use setUp() instead of setUpTestData() to create a fresh user for each test.
    This ensures test isolation but is slightly slower than setUpTestData().
    """

    def setUp(self):
        """Create test user and client for each test"""
        self.client = Client()
        self.user = create_test_user(
            first_name='Test',
            last_name='User',
            email='testuser@example.com'
        )

    def login_test_user(self):
        """Helper method to login the test user"""
        return self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

    def test_account_view_requires_login(self):
        """Test account page redirects to login when not authenticated"""
        response = self.client.get(reverse('account'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_account_view_accessible_when_logged_in(self):
        """Test account page accessible to authenticated users"""
        self.login_test_user()

        response = self.client.get(reverse('account'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Account Settings')
        self.assertContains(response, self.user.email)
        self.assertContains(response, self.user.username)

    def test_update_email_success(self):
        """Test successful email update"""
        self.login_test_user()

        new_email = 'newemail@example.com'
        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_EMAIL.value,
            'new_email': new_email,
            'current_password': self.user._test_password
        })

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, new_email)
        self.assertContains(response, 'Email address updated successfully!')

    def test_update_email_wrong_password(self):
        """Test email update fails with wrong password"""
        self.login_test_user()

        old_email = self.user.email
        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_EMAIL.value,
            'new_email': 'newemail@example.com',
            'current_password': 'wrongpassword'
        })

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, old_email)
        self.assertContains(response, 'Current password is incorrect')

    def test_update_email_invalid_format(self):
        """Test email update fails with invalid email format"""
        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_EMAIL.value,
            'new_email': 'notanemail',
            'current_password': self.user._test_password
        })

        self.assertContains(response, 'Please enter a valid email address')

    def test_update_email_already_exists(self):
        """Test email update fails if email already in use"""
        other_user = create_test_user(email='other@example.com')

        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_EMAIL.value,
            'new_email': other_user.email,
            'current_password': self.user._test_password
        })

        self.assertContains(response, 'This email is already in use')

    def test_update_name_success(self):
        """Test successful name update"""
        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_NAME.value,
            'first_name': 'NewFirst',
            'last_name': 'NewLast'
        })

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'NewFirst')
        self.assertEqual(self.user.last_name, 'NewLast')
        self.assertContains(response, 'Name updated successfully!')

    def test_update_name_empty_first_name(self):
        """Test name update fails with empty first name"""
        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        old_first_name = self.user.first_name
        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_NAME.value,
            'first_name': '',
            'last_name': 'NewLast'
        })

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, old_first_name)
        self.assertContains(response, 'First name cannot be empty')

    def test_update_username_success(self):
        """Test successful username update"""
        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        new_username = 'newusername'
        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_USERNAME.value,
            'new_username': new_username
        })

        self.user.refresh_from_db()
        self.assertEqual(self.user.username, new_username)
        self.assertContains(response, 'Username updated')

    def test_update_username_already_taken(self):
        """Test username update fails if username already exists"""
        other_user = create_test_user(username='taken')

        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        old_username = self.user.username
        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_USERNAME.value,
            'new_username': other_user.username
        })

        self.user.refresh_from_db()
        self.assertEqual(self.user.username, old_username)
        self.assertContains(response, 'This username is already taken')

    def test_update_username_empty(self):
        """Test username update fails with empty username"""
        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_USERNAME.value,
            'new_username': ''
        })

        self.assertContains(response, 'Username cannot be empty')

    def test_update_password_success(self):
        """Test successful password update"""
        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        new_password = 'NewSecurePassword123!'
        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_PASSWORD.value,
            'current_password_pwd': self.user._test_password,
            'new_password': new_password,
            'confirm_password': new_password
        })

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        self.assertContains(response, 'Password updated successfully!')

        # Verify user is still logged in
        self.assertIn('_auth_user_id', self.client.session)

    def test_update_password_wrong_current(self):
        """Test password update fails with wrong current password"""
        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_PASSWORD.value,
            'current_password_pwd': 'wrongpassword',
            'new_password': 'NewPassword123!',
            'confirm_password': 'NewPassword123!'
        })

        self.assertContains(response, 'Current password is incorrect')

    def test_update_password_mismatch(self):
        """Test password update fails when passwords don't match"""
        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_PASSWORD.value,
            'current_password_pwd': self.user._test_password,
            'new_password': 'NewPassword123!',
            'confirm_password': 'DifferentPassword123!'
        })

        self.assertContains(response, 'New passwords do not match')

    def test_update_password_too_short(self):
        """Test password update fails with password too short"""
        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_PASSWORD.value,
            'current_password_pwd': self.user._test_password,
            'new_password': 'short',
            'confirm_password': 'short'
        })

        self.assertContains(response, 'at least 8 characters')

    def test_invalid_action(self):
        """Test account view handles invalid action gracefully"""
        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        response = self.client.post(reverse('account'), {
            'action': 'invalid_action',
            'some_data': 'test'
        })

        # Should return 200 and show account page (no error crash)
        self.assertEqual(response.status_code, 200)

    def test_xss_attempt_in_name_field(self):
        """Test XSS protection in name update"""
        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        xss_payload = '<script>alert("XSS")</script>'
        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_NAME.value,
            'first_name': xss_payload,
            'last_name': 'Test'
        })

        self.user.refresh_from_db()
        # Django automatically escapes HTML, so the actual data is stored
        # but it's escaped when rendered
        self.assertEqual(self.user.first_name, xss_payload)
        # Verify it's escaped in response (not executed)
        self.assertNotContains(response, xss_payload, html=False)
        self.assertContains(response, '&lt;script&gt;', html=False)

    def test_sql_injection_attempt_in_username(self):
        """Test SQL injection protection in username update"""
        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        sql_payload = "admin' OR '1'='1"
        old_username = self.user.username
        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_USERNAME.value,
            'new_username': sql_payload
        })

        self.user.refresh_from_db()
        # Django's ORM prevents SQL injection - the string is escaped
        # The update should succeed with the literal string
        self.assertEqual(self.user.username, sql_payload)

    def test_account_view_query_optimization(self):
        """Test account view uses optimal number of database queries"""
        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        # GET request should minimize queries
        # Queries: 1=session read, 2=user, 3=user profile (for avatar display),
        #          4-6=session update (savepoint, update, release)
        with self.assertNumQueries(6):
            response = self.client.get(reverse('account'))
            self.assertEqual(response.status_code, 200)

    def test_unauthorized_post_without_login(self):
        """Test POST to account without authentication redirects to login"""
        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_EMAIL.value,
            'new_email': 'hacker@example.com',
            'current_password': 'anything'
        })

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_concurrent_password_update(self):
        """Test password update with stale user session

        When password is changed externally, Django invalidates the session
        and the user is logged out, resulting in a redirect to login.
        """
        self.client.login(
            username=self.user.username,
            password=self.user._test_password
        )

        # Store old password for later use
        old_password = self.user._test_password

        # Simulate another process updating the password
        self.user.set_password('NewPasswordFromElsewhere123!')
        self.user.save()

        # Try to update password with old password
        # Django should redirect to login since session is now invalid
        response = self.client.post(reverse('account'), {
            'action': AccountAction.UPDATE_PASSWORD.value,
            'current_password_pwd': old_password,
            'new_password': 'AnotherPassword123!',
            'confirm_password': 'AnotherPassword123!'
        })

        # Session was invalidated, so redirect to login expected
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

