from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse, resolve
from django.utils import timezone
from datetime import timedelta
from .models import UserProgress, LessonCompletion, QuizResult
from .views import landing, login_view, signup_view, logout_view, dashboard, progress_view


# ============================================================================
# MODEL TESTS (Unit Tests)
# ============================================================================

class TestUserProgressModel(TestCase):
    """Test UserProgress model functionality"""

    @classmethod
    def setUpTestData(cls):
        """Create test user and progress record"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        cls.progress = UserProgress.objects.create(
            user=cls.user,
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
        """Test calculate_quiz_accuracy handles division by zero
        
        Edge case: Ensures the method correctly returns 0.0 when total_questions
        is 0, preventing ZeroDivisionError. This is handled in the model's
        calculate_quiz_accuracy method.
        """
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

    @classmethod
    def setUpTestData(cls):
        """Create test user"""
        cls.user = User.objects.create_user(
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

    @classmethod
    def setUpTestData(cls):
        """Create test user"""
        cls.user = User.objects.create_user(
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
            'password': 'password123',
            'confirm-password': 'password123'
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
            'password': 'password123',
            'confirm-password': 'differentpass'
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
            password='password123'
        )
        
        data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'password': 'password123',
            'confirm-password': 'password123'
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
            password='password123'
        )
        
        data = {
            'name': 'John Smith',
            'email': 'john@example.com',  # Use 'john@example.com' so username will be 'john'
            'password': 'password123',
            'confirm-password': 'password123'
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


class TestLoginView(TestCase):
    """Test user login functionality"""

    @classmethod
    def setUpTestData(cls):
        """Create test user"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test'
        )
    
    def setUp(self):
        """Initialize test client"""
        self.client = Client()
        self.login_url = '/login/'

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

    @classmethod
    def setUpTestData(cls):
        """Create test user"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def setUp(self):
        """Initialize test client"""
        self.client = Client()
        self.logout_url = '/logout/'

    def test_logout_successful(self):
        """Test logout successfully logs out user"""
        # Log in first
        self.client.force_login(self.user)
        self.assertTrue(self.user.is_authenticated)
        
        # Logout
        response = self.client.get(self.logout_url)
        
        # Should redirect to landing page
        self.assertRedirects(response, reverse('landing'))
        
        # User should not be authenticated
        response = self.client.get(reverse('landing'))
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout_redirect_to_landing(self):
        """Test logout redirects to landing page"""
        self.client.force_login(self.user)
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, reverse('landing'))


# ============================================================================
# PROGRESS DASHBOARD TESTS (Integration Tests)
# ============================================================================

class TestProgressView(TestCase):
    """Test progress dashboard view"""

    @classmethod
    def setUpTestData(cls):
        """Create test user"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def setUp(self):
        """Initialize test client"""
        self.client = Client()
        self.progress_url = '/progress/'

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

    @classmethod
    def setUpTestData(cls):
        """Create test user"""
        cls.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def setUp(self):
        """Initialize test client"""
        self.client = Client()
        self.dashboard_url = '/dashboard/'

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
