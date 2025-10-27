"""
View tests for all application views.
Covers authentication (signup, login, logout), core views (landing, dashboard, progress),
account management, password recovery, and onboarding views.
"""
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.cache import cache

from home.models import UserProgress, UserProfile, OnboardingQuestion, OnboardingAttempt
from .test_utils import create_test_user


# =============================================================================
# AUTHENTICATION VIEWS
# =============================================================================

class AuthenticationViewsTest(TestCase):
    """Test signup, login, and logout views"""
    
    def setUp(self):
        self.client = Client()
        cache.clear()  # Clear rate limiting cache
    
    def test_signup_success(self):
        """Test successful user signup"""
        response = self.client.post('/signup/', {
            'name': 'John Doe',
            'email': 'john@example.com',
            'password': 'SecurePass123!',
            'confirm-password': 'SecurePass123!'
        })
        self.assertRedirects(response, reverse('dashboard'))  # Auto-login redirects to dashboard
        self.assertTrue(User.objects.filter(email='john@example.com').exists())
    
    def test_signup_password_mismatch(self):
        """Test signup fails with mismatched passwords"""
        response = self.client.post('/signup/', {
            'name': 'John Doe',
            'email': 'john@example.com',
            'password': 'Pass123!',
            'confirm-password': 'Different123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='john@example.com').exists())
    
    def test_login_success_with_email(self):
        """Test successful login with email"""
        user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        response = self.client.post('/login/', {
            'username_or_email': 'test@example.com',
            'password': 'pass123'
        })
        self.assertRedirects(response, reverse('dashboard'))  # Login redirects to dashboard
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
    def test_login_success_with_username(self):
        """Test successful login with username"""
        user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        response = self.client.post('/login/', {
            'username_or_email': 'testuser',
            'password': 'pass123'
        })
        self.assertRedirects(response, reverse('dashboard'))  # Login redirects to dashboard
    
    def test_login_invalid_credentials(self):
        """Test login fails with wrong password"""
        User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        response = self.client.post('/login/', {
            'username_or_email': 'testuser',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
    
    def test_logout(self):
        """Test logout"""
        user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        self.client.force_login(user)
        response = self.client.get('/logout/')
        self.assertEqual(response.status_code, 302)


# =============================================================================
# CORE PAGE VIEWS
# =============================================================================

class CorePageViewsTest(TestCase):
    """Test landing, dashboard, progress pages"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
    
    def test_landing_page_accessible(self):
        """Test landing page loads"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_dashboard_requires_login(self):
        """Test dashboard redirects if not authenticated"""
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_dashboard_accessible_when_logged_in(self):
        """Test authenticated user can access dashboard"""
        self.client.force_login(self.user)
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
    
    def test_progress_view_authenticated(self):
        """Test progress view for authenticated user"""
        self.client.force_login(self.user)
        response = self.client.get('/progress/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('total_minutes', response.context)
        self.assertIn('weekly_minutes', response.context)
    
    def test_progress_view_guest(self):
        """Test progress view for guest shows CTA"""
        response = self.client.get('/progress/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['total_minutes'])


# =============================================================================
# ACCOUNT MANAGEMENT VIEWS
# =============================================================================

class AccountManagementTest(TestCase):
    """Test account settings page"""
    
    def setUp(self):
        self.client = Client()
        self.user = create_test_user()
        self.client.login(username=self.user.username, password=self.user._test_password)
    
    def test_account_page_requires_login(self):
        """Test account page requires authentication"""
        self.client.logout()
        response = self.client.get('/account/')
        self.assertEqual(response.status_code, 302)
    
    def test_update_email_success(self):
        """Test email update"""
        response = self.client.post('/account/', {
            'action': 'update_email',
            'new_email': 'newemail@example.com',
            'current_password': self.user._test_password
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'newemail@example.com')
    
    def test_update_password_success(self):
        """Test password update"""
        new_pass = 'NewSecure123!'
        response = self.client.post('/account/', {
            'action': 'update_password',
            'current_password_pwd': self.user._test_password,
            'new_password': new_pass,
            'confirm_password': new_pass
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_pass))


# =============================================================================
# PASSWORD RECOVERY VIEWS
# =============================================================================

class PasswordRecoveryTest(TestCase):
    """Test forgot password and username"""
    
    def setUp(self):
        self.client = Client()
        self.user = create_test_user(email='user@example.com')
    
    def test_forgot_password_page_loads(self):
        """Test forgot password page accessible"""
        response = self.client.get('/forgot-password/')
        self.assertEqual(response.status_code, 200)
    
    def test_forgot_password_sends_email(self):
        """Test password reset email sent"""
        from django.core import mail
        response = self.client.post('/forgot-password/', {'email': self.user.email})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
    
    def test_forgot_username_page_loads(self):
        """Test forgot username page accessible"""
        response = self.client.get('/forgot-username/')
        self.assertEqual(response.status_code, 200)


# =============================================================================
# ONBOARDING VIEWS
# =============================================================================

class OnboardingViewsTest(TestCase):
    """Test onboarding assessment views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        
        # Create 10 test questions
        for i in range(1, 11):
            difficulty = 'A1' if i <= 4 else ('A2' if i <= 7 else 'B1')
            points = 1 if difficulty == 'A1' else (2 if difficulty == 'A2' else 3)
            OnboardingQuestion.objects.create(
                question_number=i, question_text=f'Q{i}', language='Spanish',
                difficulty_level=difficulty, option_a='A', option_b='B',
                option_c='C', option_d='D', correct_answer='A', difficulty_points=points
            )
    
    def test_welcome_page_accessible(self):
        """Test onboarding welcome page loads"""
        response = self.client.get('/onboarding/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/welcome.html')
    
    def test_quiz_loads_questions(self):
        """Test quiz page loads 10 questions"""
        response = self.client.get('/onboarding/quiz/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['questions'].count(), 10)
    
    def test_quiz_creates_attempt_for_guest(self):
        """Test quiz creates attempt for guest"""
        response = self.client.get('/onboarding/quiz/')
        attempt_id = response.context['attempt_id']
        attempt = OnboardingAttempt.objects.get(id=attempt_id)
        self.assertIsNone(attempt.user)
        self.assertIsNotNone(attempt.session_key)
    
    def test_quiz_creates_attempt_for_authenticated(self):
        """Test quiz creates attempt for authenticated user"""
        self.client.force_login(self.user)
        response = self.client.get('/onboarding/quiz/')
        attempt_id = response.context['attempt_id']
        attempt = OnboardingAttempt.objects.get(id=attempt_id)
        self.assertEqual(attempt.user, self.user)
    
    def test_submit_quiz_success(self):
        """Test quiz submission calculates level"""
        attempt = OnboardingAttempt.objects.create(user=self.user, language='Spanish')
        questions = OnboardingQuestion.objects.all()
        
        answers = [{'question_id': q.id, 'answer': 'A', 'time_taken': 10} for q in questions]
        data = {'attempt_id': attempt.id, 'answers': answers}
        
        response = self.client.post(
            '/onboarding/submit/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])
        self.assertEqual(result['level'], 'B1')  # All correct
    
    def test_submit_validates_answer_count(self):
        """Test submit rejects incomplete quiz"""
        attempt = OnboardingAttempt.objects.create(user=self.user, language='Spanish')
        questions = list(OnboardingQuestion.objects.all()[:5])  # Only 5 answers
        
        answers = [{'question_id': q.id, 'answer': 'A', 'time_taken': 10} for q in questions]
        data = {'attempt_id': attempt.id, 'answers': answers}
        
        response = self.client.post(
            '/onboarding/submit/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_results_page_shows_level(self):
        """Test results page displays calculated level"""
        from django.utils import timezone
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish',
            calculated_level='A2',
            total_score=12,
            total_possible=19,
            completed_at=timezone.now()
        )
        
        response = self.client.get(f'/onboarding/results/?attempt={attempt.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['attempt'], attempt)
