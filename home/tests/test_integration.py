"""
Integration tests for complete user flows.
Tests end-to-end scenarios that span multiple views and components.
"""
import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from home.models import OnboardingAttempt, OnboardingQuestion, UserProfile


def create_test_questions():
    """Helper to create 10 test questions"""
    questions = []
    for i in range(1, 11):
        difficulty = 'A1' if i <= 4 else ('A2' if i <= 7 else 'B1')
        points = 1 if difficulty == 'A1' else (2 if difficulty == 'A2' else 3)
        question = OnboardingQuestion.objects.create(
            question_number=i, question_text=f'Q{i}', language='Spanish',
            difficulty_level=difficulty, option_a='A', option_b='B',
            option_c='C', option_d='D', correct_answer='A', difficulty_points=points
        )
        questions.append(question)
    return questions


# =============================================================================
# AUTHENTICATION FLOWS
# =============================================================================

class AuthenticationFlowTest(TestCase):
    """Test complete authentication user journeys"""
    
    def test_signup_to_dashboard_flow(self):
        """Test user signup → auto-login → dashboard"""
        client = Client()
        
        # Step 1: Sign up
        response = client.post('/signup/', {
            'name': 'John Doe',
            'email': 'john@example.com',
            'password': 'SecurePass123!',
            'confirm-password': 'SecurePass123!'
        })
        self.assertRedirects(response, reverse('dashboard'))  # Auto-login redirects to dashboard
        
        # Step 2: Verify user created and logged in
        user = User.objects.get(email='john@example.com')
        self.assertIsNotNone(user)
        
        # Step 3: Access dashboard (should work without login)
        response = client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
    
    def test_login_redirect_to_next(self):
        """Test login redirects to 'next' parameter"""
        client = Client()
        _ = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        
        # Try to access protected page
        response = client.get('/dashboard/')
        self.assertIn('/login/', response.url)
        
        # Login with next parameter
        response = client.post('/login/?next=/dashboard/', {
            'username_or_email': 'testuser',
            'password': 'pass123'
        })
        self.assertRedirects(response, '/dashboard/')


# =============================================================================
# ONBOARDING FLOWS
# =============================================================================

class OnboardingFlowTest(TestCase):
    """Test complete onboarding assessment journeys"""
    
    def setUp(self):
        self.questions = create_test_questions()
    
    def test_guest_complete_quiz_and_signup(self):
        """Test guest completes quiz → signs up → results saved"""
        client = Client()
        
        # Step 1: Guest starts quiz
        response = client.get('/onboarding/quiz/')
        self.assertEqual(response.status_code, 200)
        attempt_id = response.context['attempt_id']
        
        # Step 2: Guest submits answers (all correct)
        answers = [{'question_id': q.id, 'answer': 'A', 'time_taken': 10} for q in self.questions]
        response = client.post(
            '/onboarding/submit/',
            data=json.dumps({'attempt_id': attempt_id, 'answers': answers}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result['level'], 'B1')
        
        # Step 3: Guest signs up
        response = client.post('/signup/', {
            'name': 'John Doe',
            'email': 'john@example.com',
            'password': 'SecurePass123!',
            'confirm-password': 'SecurePass123!'
        })
        
        # Step 4: Verify results saved to user profile
        user = User.objects.get(email='john@example.com')
        profile = UserProfile.objects.get(user=user)
        self.assertTrue(profile.has_completed_onboarding)
        self.assertEqual(profile.proficiency_level, 3)  # B1 -> 3
        
        # Step 5: Verify attempt linked to user
        attempt = OnboardingAttempt.objects.get(id=attempt_id)
        self.assertEqual(attempt.user, user)
    
    def test_guest_complete_quiz_and_login(self):
        """Test guest completes quiz → logs in → results saved"""
        client = Client()
        
        # Create existing user
        user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        
        # Step 1: Guest completes quiz
        response = client.get('/onboarding/quiz/')
        attempt_id = response.context['attempt_id']
        
        answers = [{'question_id': q.id, 'answer': 'A', 'time_taken': 10} for q in self.questions]
        client.post(
            '/onboarding/submit/',
            data=json.dumps({'attempt_id': attempt_id, 'answers': answers}),
            content_type='application/json'
        )
        
        # Step 2: Guest logs in
        response = client.post('/login/', {
            'username_or_email': 'test@example.com',
            'password': 'pass123'
        })
        
        # Step 3: Verify results saved
        profile = UserProfile.objects.get(user=user)
        self.assertTrue(profile.has_completed_onboarding)
        self.assertEqual(profile.proficiency_level, 3)  # B1 -> 3
    
    def test_authenticated_user_quiz_flow(self):
        """Test authenticated user: quiz → submit → profile updated"""
        client = Client()
        user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        client.login(username='testuser', password='pass123')
        
        # Step 1: Start quiz
        response = client.get('/onboarding/quiz/')
        attempt_id = response.context['attempt_id']
        
        # Step 2: Submit answers
        answers = [{'question_id': q.id, 'answer': 'A', 'time_taken': 10} for q in self.questions]
        response = client.post(
            '/onboarding/submit/',
            data=json.dumps({'attempt_id': attempt_id, 'answers': answers}),
            content_type='application/json'
        )
        
        # Step 3: Verify profile created
        profile = UserProfile.objects.get(user=user)
        self.assertTrue(profile.has_completed_onboarding)
        self.assertEqual(profile.proficiency_level, 3)  # B1 -> 3
    
    def test_user_can_retake_quiz_after_completion(self):
        """Test users can restart the assessment even after completing it."""
        client = Client()
        user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        client.login(username='testuser', password='pass123')
        
        # First attempt: all correct (B1)
        response = client.get('/onboarding/quiz/')
        attempt1_id = response.context['attempt_id']
        answers = [{'question_id': q.id, 'answer': 'A', 'time_taken': 10} for q in self.questions]
        client.post(
            '/onboarding/submit/',
            data=json.dumps({'attempt_id': attempt1_id, 'answers': answers}),
            content_type='application/json'
        )
        
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.proficiency_level, 3)  # B1 -> 3
        
        # Try to access quiz again - retakes are allowed
        response = client.get('/onboarding/quiz/')
        self.assertEqual(response.status_code, 200)
        second_attempt_id = response.context['attempt_id']
        self.assertNotEqual(second_attempt_id, attempt1_id)

        # Verify level stayed at B1 and attempts incremented
        profile.refresh_from_db()
        self.assertEqual(profile.proficiency_level, 3)  # B1 -> 3
        self.assertEqual(OnboardingAttempt.objects.filter(user=user).count(), 2)


# =============================================================================
# PROGRESS TRACKING FLOW
# =============================================================================

class ProgressTrackingFlowTest(TestCase):
    """Test progress tracking integration"""
    
    def test_onboarding_displays_on_progress_page(self):
        """Test completed onboarding shows on progress page"""
        client = Client()
        user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        client.login(username='testuser', password='pass123')

        # Create onboarding data
        from django.utils import timezone

        # Use auto-created profile and update it
        profile = user.profile
        profile.proficiency_level = 'A2'
        profile.has_completed_onboarding = True
        profile.onboarding_completed_at = timezone.now()
        profile.save()
        attempt = OnboardingAttempt.objects.create(
            user=user,
            language='Spanish',
            calculated_level='A2',
            total_score=12,
            total_possible=19,
            completed_at=timezone.now()
        )
        
        # Visit progress page
        response = client.get('/progress/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user_profile'], profile)
        self.assertEqual(response.context['latest_onboarding_attempt'], attempt)

