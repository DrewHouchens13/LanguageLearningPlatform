from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse, resolve
from django.utils import timezone
from datetime import timedelta
from .models import UserProgress, LessonCompletion, QuizResult
from .views import landing, login_view, signup_view, logout_view, dashboard, progress_view


# ============================================================================
# TEST UTILITIES AND FACTORIES
# ============================================================================

def create_test_user(**kwargs):
    """
    Factory method to create test users with secure, randomly generated data.

    This approach avoids hardcoded credentials in the codebase and follows
    Django testing best practices. Each test gets fresh, isolated user data.

    Args:
        **kwargs: Optional user attributes to override defaults

    Returns:
        User: Created user instance

    Usage:
        user = create_test_user()  # Random username/email
        admin = create_test_user(is_staff=True, is_superuser=True)
    """
    from django.utils.crypto import get_random_string

    # Generate random but predictable test data
    random_suffix = get_random_string(8, allowed_chars='0123456789')

    defaults = {
        'username': f'testuser_{random_suffix}',
        'email': f'test_{random_suffix}@example.com',
        'password': get_random_string(16),  # Secure random password
    }
    defaults.update(kwargs)

    password = defaults.pop('password')
    user = User.objects.create_user(**defaults)
    user.set_password(password)
    user.save()

    # Store password for login in tests
    user._test_password = password
    return user


def create_test_superuser(**kwargs):
    """
    Factory method to create test superusers with secure, random credentials.

    Returns:
        User: Created superuser instance with _test_password attribute
    """
    from django.utils.crypto import get_random_string

    random_suffix = get_random_string(8, allowed_chars='0123456789')

    defaults = {
        'username': f'admin_{random_suffix}',
        'email': f'admin_{random_suffix}@example.com',
        'password': get_random_string(16),
    }
    defaults.update(kwargs)

    password = defaults.pop('password')
    user = User.objects.create_superuser(**defaults)
    user.set_password(password)
    user.save()

    # Store password for login in tests
    user._test_password = password
    return user


# ============================================================================
# BASE TEST CLASSES
# ============================================================================

class AdminTestCase(TestCase):
    """
    Base class for admin-related tests.
    Uses factory methods to generate secure test data without hardcoded credentials.
    """

    @classmethod
    def setUpTestData(cls):
        """Create reusable admin user with randomly generated credentials"""
        cls.admin_user = create_test_superuser()

    def setUp(self):
        """Set up test client and login as admin (runs before each test)"""
        self.client = Client()
        self.client.login(
            username=self.admin_user.username,
            password=self.admin_user._test_password
        )


# ============================================================================
# MODEL TESTS (Unit Tests)
# ============================================================================

class TestUserProgressModel(TestCase):
    """Test UserProgress model functionality"""

    def setUp(self):
        """Create test user and progress record"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.progress = UserProgress.objects.create(
            user=self.user,
            total_minutes_studied=120,
            total_lessons_completed=5,
            total_quizzes_taken=3,
            overall_quiz_accuracy=85.5
        )

    def test_user_progress_creation(self):
        """Test UserProgress is created with correct default values"""
        new_user = User.objects.create_user(username='newuser', email='new@example.com')
        new_progress = UserProgress.objects.create(user=new_user)
        
        self.assertEqual(new_progress.total_minutes_studied, 0)
        self.assertEqual(new_progress.total_lessons_completed, 0)
        self.assertEqual(new_progress.total_quizzes_taken, 0)
        self.assertEqual(new_progress.overall_quiz_accuracy, 0.0)
        self.assertIsNotNone(new_progress.created_at)
        self.assertIsNotNone(new_progress.updated_at)

    def test_user_progress_string_representation(self):
        """Test __str__ method returns correct format"""
        expected = f"Progress for {self.user.username}"
        self.assertEqual(str(self.progress), expected)

    def test_calculate_quiz_accuracy_no_quizzes(self):
        """Test calculate_quiz_accuracy returns 0 when no quizzes exist"""
        accuracy = self.progress.calculate_quiz_accuracy()
        self.assertEqual(accuracy, 0.0)

    def test_calculate_quiz_accuracy_single_quiz(self):
        """Test calculate_quiz_accuracy with one quiz"""
        QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            quiz_title='Basic Spanish',
            score=8,
            total_questions=10
        )
        accuracy = self.progress.calculate_quiz_accuracy()
        self.assertEqual(accuracy, 80.0)

    def test_calculate_quiz_accuracy_multiple_quizzes(self):
        """Test calculate_quiz_accuracy with multiple quizzes"""
        QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            score=8,
            total_questions=10
        )
        QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz2',
            score=15,
            total_questions=20
        )
        # Total: 23/30 = 76.7%
        accuracy = self.progress.calculate_quiz_accuracy()
        self.assertEqual(accuracy, 76.7)

    def test_calculate_quiz_accuracy_zero_total_questions(self):
        """Test calculate_quiz_accuracy handles division by zero"""
        QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            score=0,
            total_questions=0
        )
        accuracy = self.progress.calculate_quiz_accuracy()
        self.assertEqual(accuracy, 0.0)

    def test_get_weekly_stats_current_week(self):
        """Test get_weekly_stats returns correct data for current week"""
        # Create lessons completed this week
        LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson1',
            lesson_title='Lesson 1',
            duration_minutes=30
        )
        LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson2',
            lesson_title='Lesson 2',
            duration_minutes=45
        )
        
        # Create quiz results this week
        QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            score=9,
            total_questions=10
        )
        
        stats = self.progress.get_weekly_stats()
        
        self.assertEqual(stats['weekly_minutes'], 75)
        self.assertEqual(stats['weekly_lessons'], 2)
        self.assertEqual(stats['weekly_accuracy'], 90.0)

    def test_get_weekly_stats_old_data(self):
        """Test get_weekly_stats excludes data older than 7 days"""
        # Create old lesson (8 days ago)
        old_date = timezone.now() - timedelta(days=8)
        old_lesson = LessonCompletion.objects.create(
            user=self.user,
            lesson_id='old_lesson',
            duration_minutes=60
        )
        old_lesson.completed_at = old_date
        old_lesson.save()
        
        stats = self.progress.get_weekly_stats()
        
        self.assertEqual(stats['weekly_minutes'], 0)
        self.assertEqual(stats['weekly_lessons'], 0)
        self.assertEqual(stats['weekly_accuracy'], 0.0)

    def test_get_weekly_stats_no_data(self):
        """Test get_weekly_stats returns zeros when no data exists"""
        stats = self.progress.get_weekly_stats()
        
        self.assertEqual(stats['weekly_minutes'], 0)
        self.assertEqual(stats['weekly_lessons'], 0)
        self.assertEqual(stats['weekly_accuracy'], 0.0)


class TestLessonCompletionModel(TestCase):
    """Test LessonCompletion model functionality"""

    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_lesson_completion_creation(self):
        """Test LessonCompletion is created with correct fields"""
        lesson = LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson_001',
            lesson_title='Introduction to Spanish',
            duration_minutes=25
        )
        
        self.assertEqual(lesson.user, self.user)
        self.assertEqual(lesson.lesson_id, 'lesson_001')
        self.assertEqual(lesson.lesson_title, 'Introduction to Spanish')
        self.assertEqual(lesson.duration_minutes, 25)
        self.assertIsNotNone(lesson.completed_at)

    def test_lesson_completion_ordering(self):
        """Test LessonCompletion ordering is most recent first"""
        lesson1 = LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson1',
            duration_minutes=20
        )
        lesson2 = LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson2',
            duration_minutes=30
        )
        
        lessons = LessonCompletion.objects.all()
        self.assertEqual(lessons[0], lesson2)  # Most recent first
        self.assertEqual(lessons[1], lesson1)

    def test_lesson_completion_user_relationship(self):
        """Test relationship with User model"""
        LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson1',
            duration_minutes=20
        )
        
        self.assertEqual(self.user.lesson_completions.count(), 1)
        self.assertEqual(self.user.lesson_completions.first().lesson_id, 'lesson1')

    def test_lesson_completion_string_representation(self):
        """Test __str__ method returns correct format"""
        lesson = LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson_001',
            lesson_title='Spanish Basics',
            duration_minutes=30
        )
        expected = f"{self.user.username} completed Spanish Basics"
        self.assertEqual(str(lesson), expected)

    def test_lesson_completion_string_without_title(self):
        """Test __str__ method uses lesson_id when title is blank"""
        lesson = LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson_001',
            duration_minutes=30
        )
        expected = f"{self.user.username} completed lesson_001"
        self.assertEqual(str(lesson), expected)


class TestQuizResultModel(TestCase):
    """Test QuizResult model functionality"""

    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_quiz_result_creation(self):
        """Test QuizResult is created with correct fields"""
        quiz = QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz_001',
            quiz_title='Spanish Vocabulary Quiz',
            score=18,
            total_questions=20
        )
        
        self.assertEqual(quiz.user, self.user)
        self.assertEqual(quiz.quiz_id, 'quiz_001')
        self.assertEqual(quiz.quiz_title, 'Spanish Vocabulary Quiz')
        self.assertEqual(quiz.score, 18)
        self.assertEqual(quiz.total_questions, 20)
        self.assertIsNotNone(quiz.completed_at)

    def test_quiz_result_accuracy_percentage(self):
        """Test accuracy_percentage property calculation"""
        quiz = QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            score=17,
            total_questions=20
        )
        self.assertEqual(quiz.accuracy_percentage, 85.0)

    def test_quiz_result_accuracy_percentage_zero_questions(self):
        """Test accuracy_percentage handles division by zero"""
        quiz = QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            score=0,
            total_questions=0
        )
        self.assertEqual(quiz.accuracy_percentage, 0.0)

    def test_quiz_result_ordering(self):
        """Test QuizResult ordering is most recent first"""
        quiz1 = QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            score=8,
            total_questions=10
        )
        quiz2 = QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz2',
            score=15,
            total_questions=20
        )
        
        quizzes = QuizResult.objects.all()
        self.assertEqual(quizzes[0], quiz2)  # Most recent first
        self.assertEqual(quizzes[1], quiz1)

    def test_quiz_result_user_relationship(self):
        """Test relationship with User model"""
        QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            score=8,
            total_questions=10
        )
        
        self.assertEqual(self.user.quiz_results.count(), 1)
        self.assertEqual(self.user.quiz_results.first().quiz_id, 'quiz1')

    def test_quiz_result_string_representation(self):
        """Test __str__ method returns correct format"""
        quiz = QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz_001',
            quiz_title='Vocabulary Test',
            score=18,
            total_questions=20
        )
        expected = f"{self.user.username} - Vocabulary Test: 18/20"
        self.assertEqual(str(quiz), expected)


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
        
        # Should redirect to landing page
        self.assertRedirects(response, reverse('landing'))
        
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
        """Test signup with duplicate email (User model allows duplicate emails)"""
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
        
        # Django User model allows duplicate emails, so signup succeeds
        # Username 'john' will be taken, so it becomes 'john1'
        self.assertRedirects(response, reverse('landing'))
        self.assertEqual(User.objects.filter(email='john@example.com').count(), 2)

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
        
        # Should redirect successfully
        self.assertRedirects(response, reverse('landing'))
        
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
        self.assertRedirects(response, reverse('landing'))

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

    def test_login_successful(self):
        """Test successful login with valid credentials"""
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)
        
        # Should redirect to landing page
        self.assertRedirects(response, reverse('landing'))
        
        # User should be logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_invalid_email(self):
        """Test login fails with non-existent email"""
        data = {
            'email': 'nonexistent@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)
        
        # Should render login page with error
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_invalid_password(self):
        """Test login fails with incorrect password"""
        data = {
            'email': 'test@example.com',
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
        self.assertRedirects(response, reverse('landing'))

    def test_login_redirect_to_next_parameter(self):
        """Test login redirects to 'next' parameter after successful login"""
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(f"{self.login_url}?next=/dashboard/", data)
        
        # Should redirect to dashboard
        self.assertRedirects(response, '/dashboard/')


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
        response = self.client.get(self.landing_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin')
        self.assertContains(response, '/admin/')

    def test_admin_button_hidden_for_regular_users(self):
        """Test admin button does not appear for regular users"""
        self.client.force_login(self.regular_user)
        response = self.client.get(self.landing_url)

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
        response = self.client.get(self.landing_url)

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
# ADMIN TESTS
# ============================================================================

class TestAdminCustomActions(TestCase):
    """Test custom admin actions for user management"""

    def setUp(self):
        """Create test users and admin user"""
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldSecurePass456!@#'
        )
        self.test_user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='OldSecurePass456!@#'
        )

    def test_reset_password_to_default_action(self):
        """Test admin action to reset user password to secure random password"""
        from home.admin import reset_password_to_default
        from django.contrib.admin.sites import AdminSite
        from django.http import HttpRequest
        from django.contrib.auth.admin import UserAdmin
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.messages import get_messages

        # Store old password
        old_password = self.test_user.password

        # Create mock request and queryset
        request = HttpRequest()
        # Setup messages framework
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = User.objects.filter(username='testuser')

        # Execute the action
        reset_password_to_default(UserAdmin(User, AdminSite()), request, queryset)

        # Verify password was changed
        self.test_user.refresh_from_db()
        self.assertNotEqual(self.test_user.password, old_password)

        # Verify a message was sent with the new password
        messages = list(get_messages(request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Passwords reset for 1 user(s)', str(messages[0]))
        self.assertIn('SAVE THESE SECURELY', str(messages[0]))

    def test_make_staff_admin_action(self):
        """Test admin action to make user an administrator"""
        from home.admin import make_staff_admin
        from django.contrib.admin.sites import AdminSite
        from django.http import HttpRequest
        from django.contrib.auth.admin import UserAdmin
        from django.contrib.messages.storage.fallback import FallbackStorage

        # Verify user is not admin initially
        self.assertFalse(self.test_user.is_staff)
        self.assertFalse(self.test_user.is_superuser)

        request = HttpRequest()
        # Setup messages framework
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = User.objects.filter(username='testuser')

        # Execute the action
        make_staff_admin(UserAdmin(User, AdminSite()), request, queryset)

        # Verify user is now admin
        self.test_user.refresh_from_db()
        self.assertTrue(self.test_user.is_staff)
        self.assertTrue(self.test_user.is_superuser)

    def test_remove_admin_privileges_action(self):
        """Test admin action to remove admin privileges"""
        from home.admin import remove_admin_privileges
        from django.contrib.admin.sites import AdminSite
        from django.http import HttpRequest
        from django.contrib.auth.admin import UserAdmin
        from django.contrib.messages.storage.fallback import FallbackStorage

        # Make user admin first
        self.test_user.is_staff = True
        self.test_user.is_superuser = True
        self.test_user.save()

        request = HttpRequest()
        # Setup messages framework
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = User.objects.filter(username='testuser')

        # Execute the action
        remove_admin_privileges(UserAdmin(User, AdminSite()), request, queryset)

        # Verify admin privileges removed
        self.test_user.refresh_from_db()
        self.assertFalse(self.test_user.is_staff)
        self.assertFalse(self.test_user.is_superuser)

    def test_reset_user_progress_action(self):
        """Test admin action to reset user progress"""
        from home.admin import reset_user_progress
        from django.contrib.admin.sites import AdminSite
        from django.http import HttpRequest
        from django.contrib.auth.admin import UserAdmin
        from django.contrib.messages.storage.fallback import FallbackStorage

        # Create progress data for user
        progress = UserProgress.objects.create(
            user=self.test_user,
            total_minutes_studied=100,
            total_lessons_completed=10,
            total_quizzes_taken=5,
            overall_quiz_accuracy=85.0
        )
        LessonCompletion.objects.create(
            user=self.test_user,
            lesson_id='lesson1',
            duration_minutes=30
        )
        QuizResult.objects.create(
            user=self.test_user,
            quiz_id='quiz1',
            score=8,
            total_questions=10
        )

        request = HttpRequest()
        # Setup messages framework
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = User.objects.filter(username='testuser')

        # Execute the action
        reset_user_progress(UserAdmin(User, AdminSite()), request, queryset)

        # Verify progress was reset
        progress.refresh_from_db()
        self.assertEqual(progress.total_minutes_studied, 0)
        self.assertEqual(progress.total_lessons_completed, 0)
        self.assertEqual(progress.total_quizzes_taken, 0)
        self.assertEqual(progress.overall_quiz_accuracy, 0.0)

        # Verify lesson completions and quiz results deleted
        self.assertEqual(self.test_user.lesson_completions.count(), 0)
        self.assertEqual(self.test_user.quiz_results.count(), 0)

    def test_reset_progress_stats_action(self):
        """Test admin action to reset UserProgress statistics"""
        from home.admin import reset_progress_stats
        from django.contrib.admin.sites import AdminSite
        from django.http import HttpRequest
        from home.admin import UserProgressAdmin
        from django.contrib.messages.storage.fallback import FallbackStorage

        # Create progress data
        progress = UserProgress.objects.create(
            user=self.test_user,
            total_minutes_studied=100,
            total_lessons_completed=10,
            total_quizzes_taken=5,
            overall_quiz_accuracy=85.0
        )

        request = HttpRequest()
        # Setup messages framework
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = UserProgress.objects.filter(user=self.test_user)

        # Execute the action
        reset_progress_stats(UserProgressAdmin(UserProgress, AdminSite()), request, queryset)

        # Verify stats were reset
        progress.refresh_from_db()
        self.assertEqual(progress.total_minutes_studied, 0)
        self.assertEqual(progress.total_lessons_completed, 0)
        self.assertEqual(progress.total_quizzes_taken, 0)
        self.assertEqual(progress.overall_quiz_accuracy, 0.0)

    def test_admin_page_accessible_for_superuser(self):
        """Test that admin page is accessible for superuser"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)

    def test_admin_page_not_accessible_for_regular_user(self):
        """Test that admin page is not accessible for regular user"""
        self.client.login(username='testuser', password='OldSecurePass456!@#')
        response = self.client.get('/admin/')
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)

    def test_admin_user_list_display(self):
        """Test custom user admin list display"""
        from home.admin import CustomUserAdmin
        from django.contrib.admin.sites import AdminSite

        admin = CustomUserAdmin(User, AdminSite())

        expected_fields = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'date_joined', 'last_login')
        self.assertEqual(admin.list_display, expected_fields)

    def test_get_progress_info_with_progress(self):
        """Test get_progress_info displays user progress data"""
        from home.admin import CustomUserAdmin
        from django.contrib.admin.sites import AdminSite

        # Create user with progress
        progress = UserProgress.objects.create(
            user=self.test_user,
            total_minutes_studied=150,
            total_lessons_completed=10,
            total_quizzes_taken=5,
            overall_quiz_accuracy=85.0
        )

        # Create some lesson completions and quiz results
        LessonCompletion.objects.create(
            user=self.test_user,
            lesson_id='lesson1',
            duration_minutes=30
        )
        QuizResult.objects.create(
            user=self.test_user,
            quiz_id='quiz1',
            score=8,
            total_questions=10
        )

        admin = CustomUserAdmin(User, AdminSite())
        progress_info = admin.get_progress_info(self.test_user)

        # Verify progress data is displayed
        self.assertIn('Total Minutes: 150', progress_info)
        self.assertIn('Total Lessons: 10', progress_info)
        self.assertIn('Total Quizzes: 5', progress_info)
        self.assertIn('Quiz Accuracy: 85.0%', progress_info)
        self.assertIn('Lesson Completions: 1', progress_info)
        self.assertIn('Quiz Results: 1', progress_info)

    def test_get_progress_info_without_progress(self):
        """Test get_progress_info when user has no progress"""
        from home.admin import CustomUserAdmin
        from django.contrib.admin.sites import AdminSite

        admin = CustomUserAdmin(User, AdminSite())
        progress_info = admin.get_progress_info(self.test_user)

        # Verify "no progress" message
        self.assertEqual(progress_info, "No progress data yet")

    def test_delete_selected_lessons_action(self):
        """
        Test delete_selected_lessons admin action.

        Verifies that the bulk delete action removes lesson completions
        and displays a success message to the admin user.
        """
        from home.admin import delete_selected_lessons, LessonCompletionAdmin
        from django.contrib.admin.sites import AdminSite
        from django.http import HttpRequest
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.messages import get_messages

        # Create lesson completions
        lesson1 = LessonCompletion.objects.create(
            user=self.test_user,
            lesson_id='lesson1',
            duration_minutes=30
        )
        lesson2 = LessonCompletion.objects.create(
            user=self.test_user,
            lesson_id='lesson2',
            duration_minutes=45
        )

        # Verify they exist
        self.assertEqual(LessonCompletion.objects.count(), 2)

        request = HttpRequest()
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = LessonCompletion.objects.all()

        # Execute the action
        delete_selected_lessons(LessonCompletionAdmin(LessonCompletion, AdminSite()), request, queryset)

        # Verify lessons were deleted
        self.assertEqual(LessonCompletion.objects.count(), 0)

        # Verify exact success message was displayed
        # Note: Using assertEqual (not assertIn) to ensure exact message matching.
        # This is intentional - if the message changes, we WANT the test to fail
        # so we know to update it and maintain consistency with user expectations.
        messages = list(get_messages(request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Successfully deleted 2 lesson completion(s)')

    def test_delete_selected_quizzes_action(self):
        """
        Test delete_selected_quizzes admin action.

        Verifies that the bulk delete action removes quiz results
        and displays a success message to the admin user.
        """
        from home.admin import delete_selected_quizzes, QuizResultAdmin
        from django.contrib.admin.sites import AdminSite
        from django.http import HttpRequest
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.messages import get_messages

        # Create quiz results
        quiz1 = QuizResult.objects.create(
            user=self.test_user,
            quiz_id='quiz1',
            score=8,
            total_questions=10
        )
        quiz2 = QuizResult.objects.create(
            user=self.test_user,
            quiz_id='quiz2',
            score=15,
            total_questions=20
        )

        # Verify they exist
        self.assertEqual(QuizResult.objects.count(), 2)

        request = HttpRequest()
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = QuizResult.objects.all()

        # Execute the action
        delete_selected_quizzes(QuizResultAdmin(QuizResult, AdminSite()), request, queryset)

        # Verify quizzes were deleted
        self.assertEqual(QuizResult.objects.count(), 0)

        # Verify exact success message was displayed
        # Note: Using exact matching to catch any unintended message changes
        messages = list(get_messages(request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Successfully deleted 2 quiz result(s)')


# ============================================================================
# ADMIN CRUD TESTS
# ============================================================================

class TestAdminCRUDOperations(AdminTestCase):
    """Test admin CRUD operations for all models."""

    def test_create_user_through_admin(self):
        """Test creating a new user through admin interface"""
        response = self.client.post('/admin/auth/user/add/', {
            'username': 'newuser',
            'password1': 'testpass123456',
            'password2': 'testpass123456',
        })

        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # User should be created
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_edit_user_through_admin(self):
        """Test editing a user through admin interface"""
        # Create a test user
        test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Edit the user
        response = self.client.post(f'/admin/auth/user/{test_user.pk}/change/', {
            'username': 'testuser',
            'email': 'newemail@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'date_joined_0': '2025-01-01',
            'date_joined_1': '00:00:00',
            'initial-date_joined_0': '2025-01-01',
            'initial-date_joined_1': '00:00:00',
        })

        # Refresh user from database
        test_user.refresh_from_db()

        # Email should be updated
        self.assertEqual(test_user.email, 'newemail@example.com')
        self.assertEqual(test_user.first_name, 'Test')

    def test_delete_user_through_admin(self):
        """Test deleting a user through admin interface"""
        # Create a test user
        test_user = User.objects.create_user(
            username='deleteuser',
            email='delete@example.com',
            password='testpass123'
        )

        user_pk = test_user.pk

        # Delete the user
        response = self.client.post(f'/admin/auth/user/{user_pk}/delete/', {
            'post': 'yes',
        })

        # Should redirect after deletion
        self.assertEqual(response.status_code, 302)

        # User should be deleted
        self.assertFalse(User.objects.filter(pk=user_pk).exists())

    def test_create_user_progress_through_admin(self):
        """Test creating UserProgress through admin interface"""
        test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        response = self.client.post('/admin/home/userprogress/add/', {
            'user': test_user.pk,
            'total_minutes_studied': 100,
            'total_lessons_completed': 5,
            'total_quizzes_taken': 3,
            'overall_quiz_accuracy': 85.5,
        })

        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # Progress should be created
        self.assertTrue(UserProgress.objects.filter(user=test_user).exists())

    def test_edit_user_progress_through_admin(self):
        """Test editing UserProgress through admin interface"""
        test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        progress = UserProgress.objects.create(
            user=test_user,
            total_minutes_studied=50
        )

        response = self.client.post(f'/admin/home/userprogress/{progress.pk}/change/', {
            'user': test_user.pk,
            'total_minutes_studied': 150,
            'total_lessons_completed': 10,
            'total_quizzes_taken': 5,
            'overall_quiz_accuracy': 90.0,
        })

        # Refresh from database
        progress.refresh_from_db()

        # Values should be updated
        self.assertEqual(progress.total_minutes_studied, 150)
        self.assertEqual(progress.total_lessons_completed, 10)

    def test_create_lesson_completion_through_admin(self):
        """Test creating LessonCompletion through admin interface"""
        test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        response = self.client.post('/admin/home/lessoncompletion/add/', {
            'user': test_user.pk,
            'lesson_id': 'lesson_001',
            'lesson_title': 'Introduction to Spanish',
            'duration_minutes': 30,
        })

        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # Lesson completion should be created
        self.assertTrue(LessonCompletion.objects.filter(lesson_id='lesson_001').exists())

    def test_create_quiz_result_through_admin(self):
        """Test creating QuizResult through admin interface"""
        test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        response = self.client.post('/admin/home/quizresult/add/', {
            'user': test_user.pk,
            'quiz_id': 'quiz_001',
            'quiz_title': 'Spanish Vocabulary',
            'score': 18,
            'total_questions': 20,
        })

        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # Quiz result should be created
        self.assertTrue(QuizResult.objects.filter(quiz_id='quiz_001').exists())


# ============================================================================
# ADMIN SEARCH AND FILTER TESTS
# ============================================================================

class TestAdminSearchAndFilters(AdminTestCase):
    """Test admin search and filter functionality."""

    @classmethod
    def setUpTestData(cls):
        """Create reusable test data (runs once per test class)"""
        super().setUpTestData()  # Create admin user from base class

        # Create test users for search/filter testing
        cls.user1 = User.objects.create_user(
            username='john',
            email='john@example.com',
            first_name='John',
            last_name='Doe'
        )
        cls.user2 = User.objects.create_user(
            username='jane',
            email='jane@example.com',
            first_name='Jane',
            last_name='Smith'
        )

    def test_user_search_by_username(self):
        """Test searching users by username in admin"""
        response = self.client.get('/admin/auth/user/', {'q': 'john'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'john')
        self.assertNotContains(response, 'jane')

    def test_user_search_by_email(self):
        """Test searching users by email in admin"""
        response = self.client.get('/admin/auth/user/', {'q': 'jane@example.com'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'jane')

    def test_user_filter_by_staff_status(self):
        """Test filtering users by staff status"""
        # Make user1 staff
        self.user1.is_staff = True
        self.user1.save()

        response = self.client.get('/admin/auth/user/', {'is_staff__exact': '1'})

        self.assertEqual(response.status_code, 200)
        # Should show john (staff) and admin, but not jane
        self.assertContains(response, 'john')
        self.assertContains(response, 'admin')

    def test_user_progress_search(self):
        """Test searching user progress by username"""
        progress = UserProgress.objects.create(
            user=self.user1,
            total_minutes_studied=100
        )

        response = self.client.get('/admin/home/userprogress/', {'q': 'john'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'john')

    def test_lesson_completion_search(self):
        """Test searching lesson completions"""
        lesson = LessonCompletion.objects.create(
            user=self.user1,
            lesson_id='spanish_101',
            lesson_title='Spanish Basics'
        )

        response = self.client.get('/admin/home/lessoncompletion/', {'q': 'Spanish'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Spanish Basics')

    def test_quiz_result_search(self):
        """Test searching quiz results"""
        quiz = QuizResult.objects.create(
            user=self.user1,
            quiz_id='quiz_spanish_001',
            quiz_title='Spanish Vocabulary Quiz',
            score=18,
            total_questions=20
        )

        response = self.client.get('/admin/home/quizresult/', {'q': 'Vocabulary'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vocabulary')

    def test_admin_list_filters_present(self):
        """Test that admin list filters are configured"""
        from home.admin import CustomUserAdmin
        from django.contrib.admin.sites import AdminSite

        admin = CustomUserAdmin(User, AdminSite())

        # Verify list_filter is configured
        self.assertIsNotNone(admin.list_filter)
        self.assertIn('is_staff', admin.list_filter)
        self.assertIn('is_superuser', admin.list_filter)


# ============================================================================
# ADMIN LOGIN FLOW TESTS
# ============================================================================

class TestAdminLoginFlow(TestCase):
    """Test admin authentication and access control."""

    @classmethod
    def setUpTestData(cls):
        """Create reusable test data with factory methods (no hardcoded credentials)"""
        # Create admin user for authentication testing
        cls.admin_user = create_test_superuser()
        # Create regular user to test access denial
        cls.regular_user = create_test_user()

    def setUp(self):
        """Set up test client (runs before each test)"""
        self.client = Client()

    def test_admin_login_successful(self):
        """Test successful admin login"""
        response = self.client.post('/admin/login/', {
            'username': self.admin_user.username,
            'password': self.admin_user._test_password,
            'next': '/admin/'
        })

        # Should redirect to admin index
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/admin/'))

    def test_admin_login_invalid_credentials(self):
        """Test admin login with invalid credentials"""
        response = self.client.post('/admin/login/', {
            'username': self.admin_user.username,
            'password': 'wrongpassword',
        })

        # Should stay on login page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter the correct username and password')

    def test_regular_user_cannot_access_admin(self):
        """Test that regular users cannot access admin"""
        self.client.login(
            username=self.regular_user.username,
            password=self.regular_user._test_password
        )

        response = self.client.get('/admin/')

        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_admin_logout(self):
        """Test admin logout"""
        # Login first
        self.client.login(
            username=self.admin_user.username,
            password=self.admin_user._test_password
        )

        # Access admin to verify logged in
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)

        # Logout (requires POST in modern Django)
        response = self.client.post('/admin/logout/')

        # Should redirect or show logout confirmation
        self.assertIn(response.status_code, [200, 302])

        # Try to access admin again (should redirect to login)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)

    def test_admin_access_user_changelist(self):
        """Test admin can access user changelist"""
        self.client.login(
            username=self.admin_user.username,
            password=self.admin_user._test_password
        )

        response = self.client.get('/admin/auth/user/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select user to change')

    def test_admin_access_user_progress_changelist(self):
        """Test admin can access UserProgress changelist"""
        self.client.login(
            username=self.admin_user.username,
            password=self.admin_user._test_password
        )

        response = self.client.get('/admin/home/userprogress/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'user progress')

    def test_admin_access_lesson_completion_changelist(self):
        """Test admin can access LessonCompletion changelist"""
        self.client.login(
            username=self.admin_user.username,
            password=self.admin_user._test_password
        )

        response = self.client.get('/admin/home/lessoncompletion/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lesson completion')

    def test_admin_access_quiz_result_changelist(self):
        """Test admin can access QuizResult changelist"""
        self.client.login(
            username=self.admin_user.username,
            password=self.admin_user._test_password
        )

        response = self.client.get('/admin/home/quizresult/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'quiz result')

    def test_unauthenticated_user_redirected_to_login(self):
        """Test unauthenticated users are redirected to admin login"""
        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_admin_index_shows_models(self):
        """Test admin index page shows all registered models"""
        self.client.login(
            username=self.admin_user.username,
            password=self.admin_user._test_password
        )

        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 200)
        # Should show User Progress models (case-sensitive based on model verbose names)
        self.assertContains(response, 'User Progress')
        self.assertContains(response, 'Lesson Completions')
        self.assertContains(response, 'Quiz Results')

