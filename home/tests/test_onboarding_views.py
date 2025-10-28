from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from home.models import OnboardingQuestion, OnboardingAttempt, UserProfile
import json


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
        user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        self.client.login(username='testuser', password='pass123')
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)

    def test_welcome_shows_profile_for_authenticated_without_onboarding(self):
        """Test welcome page shows user profile for authenticated users who haven't completed onboarding"""
        user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        profile = UserProfile.objects.create(
            user=user,
            has_completed_onboarding=False
        )
        self.client.login(username='testuser', password='pass123')
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user_profile'], profile)


class TestOnboardingQuizView(TestCase):
    """Test onboarding quiz page"""

    def setUp(self):
        """Create test questions"""
        self.client = Client()
        self.url = reverse('onboarding_quiz')
        
        # Create 10 Spanish questions
        for i in range(1, 11):
            difficulty = 'A1' if i <= 4 else ('A2' if i <= 7 else 'B1')
            points = 1 if difficulty == 'A1' else (2 if difficulty == 'A2' else 3)
            
            OnboardingQuestion.objects.create(
                question_number=i,
                question_text=f'Question {i}',
                language='Spanish',
                difficulty_level=difficulty,
                option_a='A', option_b='B', option_c='C', option_d='D',
                correct_answer='A',
                difficulty_points=points
            )

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
        user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        self.client.login(username='testuser', password='pass123')
        
        response = self.client.get(self.url)
        
        attempt_id = response.context['attempt_id']
        attempt = OnboardingAttempt.objects.get(id=attempt_id)
        self.assertEqual(attempt.user, user)

    def test_quiz_stores_attempt_id_in_session(self):
        """Test attempt ID is stored in session"""
        response = self.client.get(self.url)
        
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
        """Create test user and questions"""
        self.client = Client()
        self.url = reverse('submit_onboarding')
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        
        # Create 10 questions
        self.questions = []
        for i in range(1, 11):
            difficulty = 'A1' if i <= 4 else ('A2' if i <= 7 else 'B1')
            points = 1 if difficulty == 'A1' else (2 if difficulty == 'A2' else 3)
            
            question = OnboardingQuestion.objects.create(
                question_number=i,
                question_text=f'Question {i}',
                language='Spanish',
                difficulty_level=difficulty,
                option_a='A', option_b='B', option_c='C', option_d='D',
                correct_answer='A',
                difficulty_points=points
            )
            self.questions.append(question)

    def test_submit_requires_post(self):
        """Test submit endpoint requires POST"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 405)

    def test_submit_with_all_correct_answers(self):
        """Test submission with all correct answers"""
        # Create attempt
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
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
        self.assertEqual(profile.proficiency_level, 'B1')

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
        """Create test data"""
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        
        # Create questions and attempt
        self.questions = []
        for i in range(1, 11):
            difficulty = 'A1' if i <= 4 else ('A2' if i <= 7 else 'B1')
            points = 1 if difficulty == 'A1' else (2 if difficulty == 'A2' else 3)
            
            question = OnboardingQuestion.objects.create(
                question_number=i,
                question_text=f'Question {i}',
                language='Spanish',
                difficulty_level=difficulty,
                option_a='A', option_b='B', option_c='C', option_d='D',
                correct_answer='A',
                difficulty_points=points
            )
            self.questions.append(question)
        
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
        from django.utils import timezone
        incomplete_attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        url = f"{reverse('onboarding_results')}?attempt={incomplete_attempt.id}"
        response = self.client.get(url)
        
        self.assertRedirects(response, reverse('onboarding_quiz'))


class TestOnboardingRetakeBlocking(TestCase):
    """Test that users cannot retake onboarding once completed"""

    def setUp(self):
        """Create test user, questions, and completed attempt"""
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        
        # Create 10 questions
        for i in range(1, 11):
            difficulty = 'A1' if i <= 4 else ('A2' if i <= 7 else 'B1')
            points = 1 if difficulty == 'A1' else (2 if difficulty == 'A2' else 3)
            
            OnboardingQuestion.objects.create(
                question_number=i,
                question_text=f'Question {i}',
                language='Spanish',
                difficulty_level=difficulty,
                option_a='A', option_b='B', option_c='C', option_d='D',
                correct_answer='A',
                difficulty_points=points
            )

    def test_authenticated_user_blocked_from_retaking_welcome(self):
        """Authenticated users who completed onboarding are redirected from welcome page"""
        # Create completed user profile
        UserProfile.objects.create(
            user=self.user,
            proficiency_level='A2',
            has_completed_onboarding=True
        )
        self.client.login(username='testuser', password='pass123')
        
        response = self.client.get(reverse('onboarding_welcome'))
        
        self.assertRedirects(response, reverse('dashboard'))
        
    def test_authenticated_user_blocked_from_retaking_quiz(self):
        """Authenticated users who completed onboarding are redirected from quiz page"""
        # Create completed user profile
        UserProfile.objects.create(
            user=self.user,
            proficiency_level='A2',
            has_completed_onboarding=True
        )
        self.client.login(username='testuser', password='pass123')
        
        response = self.client.get(reverse('onboarding_quiz'))
        
        self.assertRedirects(response, reverse('dashboard'))
        
    def test_guest_with_completed_session_blocked_from_retaking(self):
        """Guests who completed in same session are blocked from retaking"""
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
        
        self.assertRedirects(response, reverse('landing'))
        
    def test_new_guest_can_still_take_onboarding(self):
        """New guests without completed session can still take onboarding"""
        response = self.client.get(reverse('onboarding_welcome'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/welcome.html')
        
    def test_results_page_still_accessible_after_completion(self):
        """Users can still view their results page after completion"""
        from django.utils import timezone
        
        # Create completed user profile
        UserProfile.objects.create(
            user=self.user,
            proficiency_level='A2',
            has_completed_onboarding=True
        )
        
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
