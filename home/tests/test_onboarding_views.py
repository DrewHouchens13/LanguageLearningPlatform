"""
Onboarding views tests.

SOFA Refactoring (Sprint 4):
- Avoid Repetition: Using test_helpers to eliminate duplicate setup code
- Single Responsibility: Each test focuses on one aspect
"""

import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from home.models import OnboardingAttempt, OnboardingQuestion, UserProfile
# SOFA: DRY - Import reusable test helpers
from home.tests.test_helpers import (create_test_onboarding_attempt,
                                     create_test_onboarding_questions,
                                     create_test_user,
                                     submit_onboarding_answers)


class TestOnboardingWelcomeView(TestCase):
    """Test onboarding welcome page"""

    def setUp(self):
        """Initialize client"""
        self.client = Client()
        self.url = reverse('onboarding_welcome')

    def test_welcome_accessible_to_guest(self):
        """Test onboarding welcome accessible without authentication"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/welcome.html')

    def test_welcome_accessible_to_authenticated(self):
        """Test onboarding welcome accessible to authenticated users"""
        _ = create_test_user()  # SOFA: DRY - Use helper to avoid duplication
        self.client.login(username='testuser', password='pass123')
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)

    def test_welcome_shows_profile_for_auth_no_onboarding(self):
        """Test welcome page shows user profile for authenticated users who haven't completed onboarding"""
        user = create_test_user()  # SOFA: DRY - Use helper to avoid duplication
        # Profile is auto-created by signal, just get it and ensure onboarding is not completed
        profile = user.profile
        profile.has_completed_onboarding = False
        profile.save()

        self.client.login(username='testuser', password='pass123')

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user_profile'], profile)


class TestOnboardingQuizView(TestCase):
    """Test onboarding quiz page"""

    def setUp(self):
        """Create test questions (SOFA: Using helper to avoid duplication)"""
        self.client = Client()
        self.url = reverse('onboarding_quiz')

        # SOFA: DRY - Use helper to create test questions (eliminates duplicate code)
        create_test_onboarding_questions()

    def test_quiz_loads_10_questions(self):
        """Test quiz page loads 10 questions"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['questions'].count(), 10)

    def test_quiz_creates_attempt_for_guest(self):
        """Test quiz creates OnboardingAttempt for guest"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        attempt_id = response.context['attempt_id']
        
        # Verify attempt exists
        attempt = OnboardingAttempt.objects.get(id=attempt_id)
        self.assertIsNone(attempt.user)
        self.assertIsNotNone(attempt.session_key)

    def test_quiz_creates_attempt_for_authenticated_user(self):
        """Test quiz creates OnboardingAttempt for authenticated user"""
        user = create_test_user()  # SOFA: DRY - Use helper to avoid duplication
        self.client.login(username='testuser', password='pass123')
        
        response = self.client.get(self.url)
        
        attempt_id = response.context['attempt_id']
        attempt = OnboardingAttempt.objects.get(id=attempt_id)
        self.assertEqual(attempt.user, user)

    def test_quiz_stores_attempt_id_in_session(self):
        """Test attempt ID is stored in session"""
        _ = self.client.get(self.url)

        self.assertIn('onboarding_attempt_id', self.client.session)

    def test_quiz_with_insufficient_questions(self):
        """Test quiz redirects when not enough questions exist"""
        # Delete some questions
        OnboardingQuestion.objects.filter(question_number__gte=8).delete()
        
        response = self.client.get(self.url)
        
        self.assertRedirects(response, reverse('onboarding_welcome'))


class TestSubmitOnboardingView(TestCase):
    """Test onboarding submission endpoint"""

    def setUp(self):
        """Create test user and questions (SOFA: Using helpers to avoid duplication)"""
        self.client = Client()
        self.url = reverse('submit_onboarding')
        self.user = create_test_user()  # SOFA: DRY - Use helper

        # SOFA: DRY - Use helper to create test questions (eliminates 14-line duplicate loop)
        self.questions = create_test_onboarding_questions()

    def test_submit_requires_post(self):
        """Test submit endpoint requires POST"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 405)

    def test_submit_with_all_correct_answers(self):
        """Test submission with all correct answers"""
        # SOFA: DRY - Use helper to create attempt
        attempt = create_test_onboarding_attempt(self.user)
        
        # Prepare submission data (all correct)
        answers = [
            {'question_id': q.id, 'answer': 'A', 'time_taken': 10}
            for q in self.questions
        ]
        
        data = {
            'attempt_id': attempt.id,
            'answers': answers
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])
        self.assertEqual(result['level'], 'B1')  # All correct → B1
        self.assertEqual(result['score'], 19)
        self.assertEqual(result['total'], 19)

    def test_submit_updates_user_profile_authenticated(self):
        """Test submission creates/updates UserProfile for authenticated user"""
        self.client.login(username='testuser', password='pass123')
        
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        answers = [
            {'question_id': q.id, 'answer': 'A', 'time_taken': 10}
            for q in self.questions
        ]
        
        data = {
            'attempt_id': attempt.id,
            'answers': answers
        }
        
        self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Check UserProfile was created
        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(profile.has_completed_onboarding)
        self.assertEqual(profile.proficiency_level, 3)  # B1 -> 3

    def test_submit_validates_answer_count(self):
        """Test submission rejects if not all 10 questions answered"""
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        # Only 5 answers
        answers = [
            {'question_id': self.questions[i].id, 'answer': 'A', 'time_taken': 10}
            for i in range(5)
        ]
        
        data = {
            'attempt_id': attempt.id,
            'answers': answers
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)

    def test_submit_prevents_double_submission(self):
        """Test submission rejects if already completed"""
        from django.utils import timezone
        
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish',
            completed_at=timezone.now()
        )
        
        answers = [
            {'question_id': q.id, 'answer': 'A', 'time_taken': 10}
            for q in self.questions
        ]
        
        data = {
            'attempt_id': attempt.id,
            'answers': answers
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)


class TestOnboardingResultsView(TestCase):
    """Test onboarding results page"""

    def setUp(self):
        """Create test data (SOFA: Using helpers to avoid duplication)"""
        self.client = Client()
        self.user = create_test_user()  # SOFA: DRY - Use helper

        # SOFA: DRY - Use helper to create test questions (eliminates 14-line duplicate loop)
        self.questions = create_test_onboarding_questions()

        # Create completed attempt for results testing
        from django.utils import timezone
        self.attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish',
            calculated_level='A2',
            total_score=12,
            total_possible=19,
            completed_at=timezone.now()
        )

    def test_results_page_loads(self):
        """Test results page loads with attempt ID"""
        url = f"{reverse('onboarding_results')}?attempt={self.attempt.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/results.html')

    def test_results_shows_attempt_data(self):
        """Test results page displays attempt data"""
        url = f"{reverse('onboarding_results')}?attempt={self.attempt.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.context['attempt'], self.attempt)
        self.assertEqual(response.context['percentage'], 63.2)

    def test_results_redirects_without_attempt_id(self):
        """Test results redirects if no attempt ID"""
        response = self.client.get(reverse('onboarding_results'))
        
        self.assertRedirects(response, reverse('onboarding_welcome'))

    def test_results_uses_session_attempt_id(self):
        """Test results uses session attempt ID if no query param"""
        session = self.client.session
        session['onboarding_attempt_id'] = self.attempt.id
        session.save()
        
        response = self.client.get(reverse('onboarding_results'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['attempt'], self.attempt)

    def test_results_redirects_if_not_completed(self):
        """Test results redirects if attempt not completed"""
        incomplete_attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        url = f"{reverse('onboarding_results')}?attempt={incomplete_attempt.id}"
        response = self.client.get(url)
        
        self.assertRedirects(response, reverse('onboarding_quiz'))


class TestOnboardingRetakeBlocking(TestCase):
    """Users should always be able to retake onboarding (legacy + new)."""

    def setUp(self):
        """Create test user and questions (SOFA: Using helpers to avoid duplication)"""
        self.client = Client()
        self.user = create_test_user()  # SOFA: DRY - Use helper

        # SOFA: DRY - Use helper to create test questions (eliminates 14-line duplicate loop)
        create_test_onboarding_questions()

    def test_auth_user_can_retake_welcome(self):
        """Authenticated users with completed onboarding can still access welcome page."""
        # Use auto-created profile and mark as completed
        profile = self.user.profile
        profile.proficiency_level = 2  # A2 -> 2
        profile.has_completed_onboarding = True
        profile.save()

        self.client.login(username='testuser', password='pass123')

        response = self.client.get(reverse('onboarding_welcome'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/welcome.html')

    def test_authenticated_user_can_retake_quiz(self):
        """Authenticated users can launch quiz even after previously completing."""
        # Use auto-created profile and mark as completed
        profile = self.user.profile
        profile.proficiency_level = 2  # A2 -> 2
        profile.has_completed_onboarding = True
        profile.save()

        self.client.login(username='testuser', password='pass123')

        response = self.client.get(reverse('onboarding_quiz'))

        self.assertEqual(response.status_code, 200)
        self.assertGreater(OnboardingAttempt.objects.count(), 0)
        
    def test_guest_with_session_done_can_retake(self):
        """Guests can restart even if prior attempt in same session was completed."""
        from django.utils import timezone

        # Create a completed guest attempt
        attempt = OnboardingAttempt.objects.create(
            user=None,
            session_key='test_session_key',
            language='Spanish',
            calculated_level='A2',
            total_score=12,
            total_possible=19,
            completed_at=timezone.now()
        )
        
        # Set session
        session = self.client.session
        session['onboarding_attempt_id'] = attempt.id
        session.save()
        
        response = self.client.get(reverse('onboarding_welcome'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/welcome.html')
        self.assertNotIn('onboarding_attempt_id', self.client.session)
        
    def test_new_guest_can_still_take_onboarding(self):
        """New guests without completed session can still take onboarding"""
        response = self.client.get(reverse('onboarding_welcome'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/welcome.html')
        
    def test_results_page_accessible_after_done(self):
        """Users can still view their results page after completion"""
        from django.utils import timezone

        # Use auto-created profile and mark as completed
        profile = self.user.profile
        profile.proficiency_level = 2  # A2 -> 2
        profile.has_completed_onboarding = True
        profile.save()
        
        # Create completed attempt
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish',
            calculated_level='A2',
            total_score=12,
            total_possible=19,
            completed_at=timezone.now()
        )
        
        self.client.login(username='testuser', password='pass123')
        
        url = f"{reverse('onboarding_results')}?attempt={attempt.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/results.html')

    def test_user_without_onboarding_can_access_welcome(self):
        """Users who haven't completed onboarding can still access welcome page"""
        self.client.login(username='testuser', password='pass123')
        
        response = self.client.get(reverse('onboarding_welcome'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/welcome.html')
