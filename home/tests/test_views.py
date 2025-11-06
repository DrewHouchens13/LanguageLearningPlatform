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

from home.views import landing, login_view, signup_view, logout_view, dashboard, progress_view


# ============================================================================
# AUTHENTICATION TESTS (Integration Tests)
# ============================================================================

class TestSignupView(TestCase):
    """Test user signup functionality"""

    def setUp(self):
        """Initialize test client"""
        self.client = Client()
        self.signup_url = '/signup/'

    def test_signup_get_request(self):
        """Test GET request renders login.html"""
        response = self.client.get(self.signup_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_signup_successful(self):
        """Test successful signup with valid data"""
        data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'password': 'securepass123',
            'confirm-password': 'securepass123'
        }
        response = self.client.post(self.signup_url, data)
        
        # Should redirect to dashboard
        self.assertRedirects(response, reverse('dashboard'))
        
        # User should be created
        self.assertTrue(User.objects.filter(email='john@example.com').exists())
        
        # User should be logged in
        user = User.objects.get(email='john@example.com')
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Doe')
        self.assertEqual(user.username, 'john')

    def test_signup_creates_user_and_logs_in(self):
        """Test signup creates user and automatically logs them in"""
        data = {
            'name': 'Jane Smith',
            'email': 'jane@example.com',
            'password': 'SecurePass123!@#',
            'confirm-password': 'SecurePass123!@#'
        }
        response = self.client.post(self.signup_url, data, follow=True)
        
        # Check if user is authenticated
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.email, 'jane@example.com')

    def test_signup_password_mismatch(self):
        """Test signup fails when passwords don't match"""
        data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'password': 'SecurePass123!@#',
            'confirm-password': 'DifferentPass456!@#'
        }
        response = self.client.post(self.signup_url, data)
        
        # Should render login page with error
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        
        # User should not be created
        self.assertFalse(User.objects.filter(email='john@example.com').exists())

    def test_signup_password_too_short(self):
        """Test signup fails when password is less than 8 characters"""
        data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'password': 'short',
            'confirm-password': 'short'
        }
        response = self.client.post(self.signup_url, data)
        
        # Should render login page with error
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        
        # User should not be created
        self.assertFalse(User.objects.filter(email='john@example.com').exists())

    def test_signup_duplicate_email(self):
        """Test signup with duplicate email is now rejected"""
        # Create existing user
        User.objects.create_user(
            username='existing',
            email='john@example.com',
            password='SecurePass123!@#'
        )
        
        data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'password': 'SecurePass123!@#',
            'confirm-password': 'SecurePass123!@#'
        }
        response = self.client.post(self.signup_url, data)
        
        # Signup now validates for duplicate emails and shows error
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        # Should still have only 1 user with this email
        self.assertEqual(User.objects.filter(email='john@example.com').count(), 1)

    def test_signup_username_collision_handling(self):
        """Test signup handles username collisions by adding numbers"""
        # Create existing user with username 'john'
        User.objects.create_user(
            username='john',
            email='john1@example.com',
            password='SecurePass123!@#'
        )
        
        data = {
            'name': 'John Smith',
            'email': 'john@example.com',  # Use 'john@example.com' so username will be 'john'
            'password': 'SecurePass123!@#',
            'confirm-password': 'SecurePass123!@#'
        }
        response = self.client.post(self.signup_url, data)
        
        # Should redirect to dashboard successfully
        self.assertRedirects(response, reverse('dashboard'))
        
        # New user should have username 'john1' since 'john' is taken
        new_user = User.objects.get(email='john@example.com')
        self.assertEqual(new_user.username, 'john1')

    def test_signup_redirect_if_authenticated(self):
        """Test authenticated users are redirected from signup page"""
        # Create and log in user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_login(user)

        response = self.client.get(self.signup_url)
        # Authenticated users redirected to parent (..), which redirects to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '..')

    def test_signup_exception_handling(self):
        """
        Test signup handles unexpected exceptions gracefully.

        When user creation fails due to an unexpected error,
        the view should handle it gracefully, display an error message,
        and ensure no partial user data is created.
        """
        from unittest.mock import patch
        from django.db import DatabaseError

        # Mock User.objects.create_user to raise a database error
        # (simulates database connection issues or constraint violations)
        with patch('home.views.User.objects.create_user') as mock_create:
            mock_create.side_effect = DatabaseError('Database connection lost')

            data = {
                'name': 'John Doe',
                'email': 'john@example.com',
                'password': 'securepass123',
                'confirm-password': 'securepass123'
            }
            response = self.client.post(self.signup_url, data)

            # Should render login page with error (not crash)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'login.html')

            # User should not be created (database transaction rolled back)
            self.assertFalse(User.objects.filter(email='john@example.com').exists())

            # Verify exact error message was set
            # Note: Using exact matching ensures consistent error messages for users
            messages = list(response.context['messages'])
            self.assertEqual(len(messages), 1)
            self.assertEqual(
                str(messages[0]),
                'An error occurred while creating your account. Please try again.'
            )

class TestLoginView(TestCase):
    """Test user login functionality"""

    def setUp(self):
        """Create test user and initialize client"""
        from django.core.cache import cache
        cache.clear()  # Clear cache to reset rate limiting between tests

        self.client = Client()
        self.login_url = '/login/'
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test'
        )

    def test_login_get_request(self):
        """Test GET request renders login.html"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_successful_with_email(self):
        """Test successful login with valid email and password"""
        data = {
            'username_or_email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)

        # Should redirect to dashboard
        self.assertRedirects(response, reverse('dashboard'))

        # User should be logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_successful_with_username(self):
        """Test successful login with valid username and password"""
        data = {
            'username_or_email': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)

        # Should redirect to dashboard
        self.assertRedirects(response, reverse('dashboard'))

        # User should be logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_invalid_email(self):
        """Test login fails with non-existent email"""
        data = {
            'username_or_email': 'nonexistent@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)

        # Should render login page with error
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_invalid_username(self):
        """Test login fails with non-existent username"""
        data = {
            'username_or_email': 'nonexistentuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)

        # Should render login page with error
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_invalid_password(self):
        """Test login fails with incorrect password"""
        data = {
            'username_or_email': 'test@example.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, data)

        # Should render login page with error
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_invalid_password_with_username(self):
        """Test login fails with incorrect password when using username"""
        data = {
            'username_or_email': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, data)

        # Should render login page with error
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_redirect_if_authenticated(self):
        """Test authenticated users are redirected from login page"""
        self.client.force_login(self.user)
        
        response = self.client.get(self.login_url)
        # Authenticated users redirected to parent (..)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '..')

    def test_login_redirect_to_next_parameter(self):
        """Test login redirects to 'next' parameter after successful login"""
        data = {
            'username_or_email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(f"{self.login_url}?next=/dashboard/", data)

        # Should redirect to dashboard
        self.assertRedirects(response, '/dashboard/')

    def test_login_redirect_to_next_parameter_with_username(self):
        """Test login with username redirects to 'next' parameter after successful login"""
        data = {
            'username_or_email': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(f"{self.login_url}?next=/dashboard/", data)

        # Should redirect to dashboard
        self.assertRedirects(response, '/dashboard/')

    def test_login_empty_username_or_email(self):
        """Test login fails with empty username/email field"""
        data = {
            'username_or_email': '',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)

        # Should render login page with error
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        self.assertContains(response, 'Please provide both username/email and password')

    def test_login_empty_password(self):
        """Test login fails with empty password field"""
        data = {
            'username_or_email': 'testuser',
            'password': ''
        }
        response = self.client.post(self.login_url, data)

        # Should render login page with error
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        self.assertContains(response, 'Please provide both username/email and password')

    def test_login_excessively_long_input(self):
        """Test login fails with excessively long username/email"""
        data = {
            'username_or_email': 'a' * 300,  # Exceeds 254 char limit
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)

        # Should render login page with error
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        self.assertContains(response, 'Invalid username/email or password')

    def test_login_invalid_characters(self):
        """Test login fails with invalid characters in username/email"""
        data = {
            'username_or_email': 'test<script>alert("xss")</script>',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)

        # Should render login page with error
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        self.assertContains(response, 'Invalid username/email or password')

    def test_login_sql_injection_attempt(self):
        """Test login prevents SQL injection attempts"""
        data = {
            'username_or_email': "admin' OR '1'='1",
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)

        # Should render login page with error (single quote is invalid)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        self.assertContains(response, 'Invalid username/email or password')

    def test_login_rate_limiting(self):
        """Test login rate limiting prevents brute force attacks"""
        data = {
            'username_or_email': 'wronguser',
            'password': 'wrongpass'
        }

        # Make 5 failed login attempts (should all be allowed)
        for i in range(5):
            response = self.client.post(self.login_url, data)
            self.assertEqual(response.status_code, 200)

        # 6th attempt should be rate limited
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        self.assertContains(response, 'Too many login attempts')

    def test_login_open_redirect_prevention(self):
        """Test login prevents open redirect attacks"""
        data = {
            'username_or_email': 'testuser',
            'password': 'testpass123'
        }

        # Try to redirect to external URL (should be blocked)
        response = self.client.post(f"{self.login_url}?next=https://evil.com", data)

        # Should redirect to dashboard instead of evil.com
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_safe_internal_redirect(self):
        """Test login allows safe internal redirects"""
        data = {
            'username_or_email': 'testuser',
            'password': 'testpass123'
        }

        # Internal redirect should be allowed
        response = self.client.post(f"{self.login_url}?next=/progress/", data)
        self.assertRedirects(response, '/progress/')

    def test_login_error_message_prevents_user_enumeration(self):
        """Test login error messages don't reveal if user exists"""
        # Non-existent user
        response1 = self.client.post(self.login_url, {
            'username_or_email': 'nonexistentuser',
            'password': 'anypassword'
        })

        # Existing user with wrong password
        response2 = self.client.post(self.login_url, {
            'username_or_email': 'testuser',
            'password': 'wrongpassword'
        })

        # Both should have the same generic error message
        messages1 = list(response1.context['messages'])
        messages2 = list(response2.context['messages'])

        self.assertEqual(len(messages1), 1)
        self.assertEqual(len(messages2), 1)
        self.assertEqual(str(messages1[0]), str(messages2[0]))
        self.assertIn('Invalid username/email or password', str(messages1[0]))

class TestLogoutView(TestCase):
    """Test user logout functionality"""

    def setUp(self):
        """Create test user and initialize client"""
        self.client = Client()
        self.logout_url = '/logout/'
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_logout_successful(self):
        """Test logout successfully logs out user"""
        # Log in first
        self.client.force_login(self.user)
        self.assertTrue(self.user.is_authenticated)

        # Logout
        response = self.client.get(self.logout_url)

        # Should redirect to landing page (absolute URL now)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse('landing')))

        # User should not be authenticated
        response = self.client.get(reverse('landing'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_redirect_to_landing(self):
        """Test logout redirects to landing page"""
        self.client.force_login(self.user)
        response = self.client.get(self.logout_url)
        # Logout now uses absolute URL redirect to avoid double prefix in admin
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse('landing')))



# ============================================================================
# PROGRESS DASHBOARD TESTS (Integration Tests)
# ============================================================================

class TestProgressView(TestCase):
    """Test progress dashboard view"""

    def setUp(self):
        """Create test user and initialize client"""
        self.client = Client()
        self.progress_url = '/progress/'
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_progress_view_authenticated_user(self):
        """Test authenticated user sees their progress data"""
        self.client.force_login(self.user)
        
        # Create progress data
        progress = UserProgress.objects.create(
            user=self.user,
            total_minutes_studied=150,
            total_lessons_completed=10,
            total_quizzes_taken=5,
            overall_quiz_accuracy=88.5
        )
        
        response = self.client.get(self.progress_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'progress.html')
        
        # Check context data
        self.assertEqual(response.context['total_minutes'], 150)
        self.assertEqual(response.context['total_lessons'], 10)
        self.assertEqual(response.context['total_quizzes'], 5)
        self.assertEqual(response.context['overall_accuracy'], 88.5)

    def test_progress_view_guest_user(self):
        """Test guest user sees None values (CTAs)"""
        response = self.client.get(self.progress_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'progress.html')
        
        # Check context data is None for guest
        self.assertIsNone(response.context['weekly_minutes'])
        self.assertIsNone(response.context['weekly_lessons'])
        self.assertIsNone(response.context['weekly_accuracy'])
        self.assertIsNone(response.context['total_minutes'])
        self.assertIsNone(response.context['total_lessons'])
        self.assertIsNone(response.context['total_quizzes'])
        self.assertIsNone(response.context['overall_accuracy'])

    def test_progress_view_auto_creates_user_progress(self):
        """Test UserProgress is auto-created on first visit"""
        self.client.force_login(self.user)
        
        # Ensure no progress exists
        self.assertFalse(UserProgress.objects.filter(user=self.user).exists())
        
        response = self.client.get(self.progress_url)
        
        # Progress should be created
        self.assertTrue(UserProgress.objects.filter(user=self.user).exists())
        self.assertEqual(response.status_code, 200)

    def test_progress_view_weekly_stats(self):
        """Test weekly stats calculation integration"""
        self.client.force_login(self.user)
        
        progress = UserProgress.objects.create(user=self.user)
        
        # Create recent lesson completions
        LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson1',
            duration_minutes=30
        )
        LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson2',
            duration_minutes=45
        )
        
        response = self.client.get(self.progress_url)
        
        # Check weekly stats in context
        self.assertEqual(response.context['weekly_minutes'], 75)
        self.assertEqual(response.context['weekly_lessons'], 2)

    def test_progress_view_context_structure(self):
        """Test context contains all required keys"""
        self.client.force_login(self.user)
        
        response = self.client.get(self.progress_url)
        
        required_keys = [
            'weekly_minutes',
            'weekly_lessons',
            'weekly_accuracy',
            'total_minutes',
            'total_lessons',
            'total_quizzes',
            'overall_accuracy'
        ]
        
        for key in required_keys:
            self.assertIn(key, response.context)

class TestDashboardView(TestCase):
    """Test dashboard view"""

    def setUp(self):
        """Create test user and initialize client"""
        self.client = Client()
        self.dashboard_url = '/dashboard/'
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_dashboard_requires_authentication(self):
        """Test dashboard redirects to login if not authenticated"""
        response = self.client.get(self.dashboard_url)
        
        # Should redirect to login with next parameter
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
        self.assertIn('next=', response.url)

    def test_dashboard_authenticated_user_access(self):
        """Test authenticated user can access dashboard"""
        self.client.force_login(self.user)
        
        response = self.client.get(self.dashboard_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')



# ============================================================================
# LANDING PAGE TESTS
# ============================================================================

class TestLandingPageAdminButton(TestCase):
    """Test admin button visibility on landing page"""

    def setUp(self):
        """Create test users"""
        self.client = Client()
        self.landing_url = '/'

        # Create regular user
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='SecurePass123!@#'
        )

        # Create staff user (admin)
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='SecurePass123!@#',
            is_staff=True,
            is_superuser=True
        )

    def test_admin_button_visible_for_staff(self):
        """Test admin button appears for staff users"""
        self.client.force_login(self.admin_user)
        # Authenticated users get redirected to dashboard
        response = self.client.get(self.landing_url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin')
        self.assertContains(response, '/admin/')

    def test_admin_button_hidden_for_regular_users(self):
        """Test admin button does not appear for regular users"""
        self.client.force_login(self.regular_user)
        # Authenticated users get redirected to dashboard
        response = self.client.get(self.landing_url, follow=True)

        self.assertEqual(response.status_code, 200)
        # Should not contain the admin link (checking for the text "Admin" with the admin-link class)
        self.assertNotContains(response, 'admin-link')

    def test_admin_button_hidden_for_anonymous_users(self):
        """Test admin button does not appear for anonymous users"""
        response = self.client.get(self.landing_url)

        self.assertEqual(response.status_code, 200)
        # Should not contain the admin link
        self.assertNotContains(response, 'admin-link')

    def test_staff_user_without_superuser_sees_admin_button(self):
        """Test staff users (even without superuser) see admin button"""
        staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='SecurePass123!@#',
            is_staff=True,
            is_superuser=False
        )
        self.client.force_login(staff_user)
        # Authenticated users get redirected to dashboard
        response = self.client.get(self.landing_url, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin')
        self.assertContains(response, '/admin/')



# ============================================================================
# URL TESTS
# ============================================================================

class TestURLRouting(TestCase):
    """Test URL patterns and routing"""

    def test_landing_url_resolves(self):
        """Test landing page URL resolves correctly"""
        url = reverse('landing')
        self.assertEqual(resolve(url).func, landing)

    def test_login_url_resolves(self):
        """Test login URL resolves correctly"""
        url = reverse('login')
        self.assertEqual(resolve(url).func, login_view)

    def test_signup_url_resolves(self):
        """Test signup URL resolves correctly"""
        url = reverse('signup')
        self.assertEqual(resolve(url).func, signup_view)

    def test_logout_url_resolves(self):
        """Test logout URL resolves correctly"""
        url = reverse('logout')
        self.assertEqual(resolve(url).func, logout_view)

    def test_dashboard_url_resolves(self):
        """Test dashboard URL resolves correctly"""
        url = reverse('dashboard')
        self.assertEqual(resolve(url).func, dashboard)

    def test_progress_url_resolves(self):
        """Test progress URL resolves correctly"""
        url = reverse('progress')
        self.assertEqual(resolve(url).func, progress_view)

    def test_url_reverse_lookups(self):
        """Test all URL reverse lookups work correctly"""
        urls = {
            'landing': '/',
            'login': '/login/',
            'signup': '/signup/',
            'logout': '/logout/',
            'dashboard': '/dashboard/',
            'progress': '/progress/',
        }
        
        for name, expected_path in urls.items():
            with self.subTest(url_name=name):
                self.assertEqual(reverse(name), expected_path)


# ============================================================================
# NAVIGATION BAR TESTS
# ============================================================================

class TestNavigationBar(TestCase):
    """Test navigation bar components including version badge"""

    def setUp(self):
        """Set up test client and test user"""
        self.client = Client()
        self.user = create_test_user()

    def test_version_badge_appears_on_landing_page(self):
        """Test version badge appears in navigation on landing page"""
        response = self.client.get(reverse('landing'))
        self.assertEqual(response.status_code, 200)
        # Check version badge HTML is present
        self.assertContains(response, 'class="version-badge"')
        self.assertContains(response, 'v2.0 - Sprint 3')

    def test_version_badge_appears_on_login_page(self):
        """Test version badge appears in navigation on login page"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="version-badge"')
        self.assertContains(response, 'v2.0 - Sprint 3')

    def test_version_badge_appears_on_dashboard(self):
        """Test version badge appears in navigation on dashboard (authenticated)"""
        self.client.login(username=self.user.username, password=self.user._test_password)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="version-badge"')
        self.assertContains(response, 'v2.0 - Sprint 3')

    def test_version_badge_appears_on_progress_page(self):
        """Test version badge appears in navigation on progress page"""
        self.client.login(username=self.user.username, password=self.user._test_password)
        response = self.client.get(reverse('progress'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="version-badge"')
        self.assertContains(response, 'v2.0 - Sprint 3')

    def test_navigation_structure_with_version(self):
        """Test navigation structure includes version badge correctly"""
        response = self.client.get(reverse('landing'))
        # Check nav-brand div contains both h1 and version badge
        content = response.content.decode('utf-8')
        self.assertIn('nav-brand', content)
        self.assertIn('Language Learning Platform', content)
        # Version badge should appear after the h1 title
        h1_index = content.find('<h1>Language Learning Platform</h1>')
        version_index = content.find('class="version-badge"')
        self.assertTrue(h1_index < version_index,
                       "Version badge should appear after h1 title in nav-brand")
