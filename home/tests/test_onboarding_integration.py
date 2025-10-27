from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from home.models import OnboardingQuestion, OnboardingAttempt, UserProfile
import json


def create_test_questions():
    """Helper to create 10 test questions"""
    questions = []
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
        questions.append(question)
    return questions


class TestCompleteGuestOnboardingFlow(TestCase):
    """Test complete onboarding flow for guest users"""

    def setUp(self):
        """Initialize client and create questions"""
        self.client = Client()
        self.questions = create_test_questions()

    def test_guest_complete_quiz_and_view_results(self):
        """Test guest can complete quiz and view results"""
        # Step 1: Visit welcome page
        response = self.client.get(reverse('onboarding_welcome'))
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Start quiz
        response = self.client.get(reverse('onboarding_quiz'))
        self.assertEqual(response.status_code, 200)
        attempt_id = response.context['attempt_id']
        
        # Step 3: Submit answers (all correct)
        answers = [
            {'question_id': q.id, 'answer': 'A', 'time_taken': 10}
            for q in self.questions
        ]
        data = {
            'attempt_id': attempt_id,
            'answers': answers
        }
        response = self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])
        self.assertEqual(result['level'], 'B1')
        
        # Step 4: View results
        results_url = f"{reverse('onboarding_results')}?attempt={attempt_id}"
        response = self.client.get(results_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['attempt'].calculated_level, 'B1')

    def test_guest_signup_after_quiz_saves_results(self):
        """Test guest signup after quiz saves onboarding results to account"""
        # Step 1: Complete quiz as guest
        response = self.client.get(reverse('onboarding_quiz'))
        attempt_id = response.context['attempt_id']
        
        answers = [
            {'question_id': q.id, 'answer': 'A', 'time_taken': 10}
            for q in self.questions
        ]
        data = {
            'attempt_id': attempt_id,
            'answers': answers
        }
        self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Step 2: Sign up
        signup_data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'password': 'SecurePass123!@#',
            'confirm-password': 'SecurePass123!@#'
        }
        response = self.client.post(reverse('signup'), signup_data)
        
        # Verify redirect to results
        self.assertRedirects(response, f'/onboarding/results/?attempt={attempt_id}', fetch_redirect_response=False)
        
        # Step 3: Verify UserProfile created with onboarding data
        user = User.objects.get(email='john@example.com')
        profile = UserProfile.objects.get(user=user)
        self.assertTrue(profile.has_completed_onboarding)
        self.assertEqual(profile.proficiency_level, 'B1')
        
        # Step 4: Verify attempt linked to user
        attempt = OnboardingAttempt.objects.get(id=attempt_id)
        self.assertEqual(attempt.user, user)

    def test_guest_login_after_quiz_saves_results(self):
        """Test guest login after quiz saves onboarding results to account"""
        # Create existing user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Pass123!@#'
        )
        
        # Step 1: Complete quiz as guest
        response = self.client.get(reverse('onboarding_quiz'))
        attempt_id = response.context['attempt_id']
        
        answers = [
            {'question_id': q.id, 'answer': 'A', 'time_taken': 10}
            for q in self.questions
        ]
        data = {
            'attempt_id': attempt_id,
            'answers': answers
        }
        self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Step 2: Login
        login_data = {
            'username_or_email': 'test@example.com',
            'password': 'Pass123!@#'
        }
        response = self.client.post(reverse('login'), login_data)
        
        # Should redirect to results
        self.assertRedirects(response, f'/onboarding/results/?attempt={attempt_id}', fetch_redirect_response=False)
        
        # Step 3: Verify UserProfile created
        profile = UserProfile.objects.get(user=user)
        self.assertTrue(profile.has_completed_onboarding)
        self.assertEqual(profile.proficiency_level, 'B1')


class TestCompleteAuthenticatedOnboardingFlow(TestCase):
    """Test complete onboarding flow for authenticated users"""

    def setUp(self):
        """Create user and questions"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Pass123!@#'
        )
        self.questions = create_test_questions()
        self.client.login(username='testuser', password='Pass123!@#')

    def test_authenticated_user_complete_quiz(self):
        """Test authenticated user can complete quiz"""
        # Step 1: Start quiz
        response = self.client.get(reverse('onboarding_quiz'))
        self.assertEqual(response.status_code, 200)
        attempt_id = response.context['attempt_id']
        
        # Verify attempt linked to user
        attempt = OnboardingAttempt.objects.get(id=attempt_id)
        self.assertEqual(attempt.user, self.user)
        
        # Step 2: Submit answers
        answers = [
            {'question_id': q.id, 'answer': 'A', 'time_taken': 10}
            for q in self.questions
        ]
        data = {
            'attempt_id': attempt_id,
            'answers': answers
        }
        response = self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps(data),
            content_type='application/json'
        )
        result = response.json()
        self.assertTrue(result['success'])
        
        # Step 3: Verify UserProfile created
        profile = UserProfile.objects.get(user=self.user)
        self.assertTrue(profile.has_completed_onboarding)
        self.assertEqual(profile.proficiency_level, 'B1')

    def test_authenticated_user_can_retake_quiz(self):
        """Test authenticated user can retake quiz and update level"""
        # First attempt - all correct (B1)
        response = self.client.get(reverse('onboarding_quiz'))
        attempt1_id = response.context['attempt_id']
        
        answers = [
            {'question_id': q.id, 'answer': 'A', 'time_taken': 10}
            for q in self.questions
        ]
        self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps({'attempt_id': attempt1_id, 'answers': answers}),
            content_type='application/json'
        )
        
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.proficiency_level, 'B1')
        
        # Second attempt - some wrong (should result in lower level)
        response = self.client.get(reverse('onboarding_quiz'))
        attempt2_id = response.context['attempt_id']
        
        # Answer first 4 correct, rest wrong
        answers_retake = [
            {'question_id': self.questions[i].id, 'answer': 'A' if i < 4 else 'D', 'time_taken': 10}
            for i in range(10)
        ]
        self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps({'attempt_id': attempt2_id, 'answers': answers_retake}),
            content_type='application/json'
        )
        
        profile.refresh_from_db()
        # 4/19 = 21.1%, 4/4 A1 (100%) → A1
        self.assertEqual(profile.proficiency_level, 'A1')
        
        # Verify both attempts exist
        self.assertEqual(OnboardingAttempt.objects.filter(user=self.user).count(), 2)


class TestOnboardingLevelCalculationIntegration(TestCase):
    """Test level calculation works correctly in complete flows"""

    def setUp(self):
        """Create client and questions"""
        self.client = Client()
        self.questions = create_test_questions()

    def test_a1_placement(self):
        """Test user gets A1 placement with poor performance"""
        response = self.client.get(reverse('onboarding_quiz'))
        attempt_id = response.context['attempt_id']
        
        # Answer only 2 A1 questions correctly, rest wrong
        answers = [
            {'question_id': self.questions[i].id, 'answer': 'A' if i < 2 else 'D', 'time_taken': 10}
            for i in range(10)
        ]
        
        response = self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps({'attempt_id': attempt_id, 'answers': answers}),
            content_type='application/json'
        )
        
        result = response.json()
        self.assertEqual(result['level'], 'A1')
        self.assertEqual(result['score'], 2)

    def test_a2_placement(self):
        """Test user gets A2 placement with moderate performance"""
        response = self.client.get(reverse('onboarding_quiz'))
        attempt_id = response.context['attempt_id']
        
        # All A1, all A2, no B1 → 4+6=10/19 = 52.6% but should be A1 (< 60%)
        # Let's get to exactly A2: All A1, 2 A2, 1 B1 = 4+4+3=11/19=57.9% still < 60%
        # Need: All A1 (4), All A2 (6), 1 B1 (3) = 13/19 = 68.4% → A2
        answers = []
        for i in range(10):
            if i < 7:  # A1 and A2 - all correct
                answers.append({'question_id': self.questions[i].id, 'answer': 'A', 'time_taken': 10})
            elif i == 7:  # First B1 - correct
                answers.append({'question_id': self.questions[i].id, 'answer': 'A', 'time_taken': 10})
            else:  # Other B1 - wrong
                answers.append({'question_id': self.questions[i].id, 'answer': 'D', 'time_taken': 10})
        
        response = self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps({'attempt_id': attempt_id, 'answers': answers}),
            content_type='application/json'
        )
        
        result = response.json()
        self.assertEqual(result['level'], 'A2')

    def test_b1_placement(self):
        """Test user gets B1 placement with strong performance"""
        response = self.client.get(reverse('onboarding_quiz'))
        attempt_id = response.context['attempt_id']
        
        # All A1, all A2, 2 out of 3 B1 → 16/19 = 84.2%, B1 pct = 66.7% → B1
        answers = []
        for i in range(10):
            if i < 9:  # First 9 correct (all A1, all A2, 2 B1)
                answers.append({'question_id': self.questions[i].id, 'answer': 'A', 'time_taken': 10})
            else:  # Last B1 wrong
                answers.append({'question_id': self.questions[i].id, 'answer': 'D', 'time_taken': 10})
        
        response = self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps({'attempt_id': attempt_id, 'answers': answers}),
            content_type='application/json'
        )
        
        result = response.json()
        self.assertEqual(result['level'], 'B1')
        self.assertEqual(result['score'], 16)


class TestOnboardingErrorHandling(TestCase):
    """Test error handling in onboarding flows"""

    def setUp(self):
        """Create client and questions"""
        self.client = Client()
        self.questions = create_test_questions()

    def test_submit_with_invalid_attempt_id(self):
        """Test submission with invalid attempt ID"""
        answers = [
            {'question_id': q.id, 'answer': 'A', 'time_taken': 10}
            for q in self.questions
        ]
        data = {
            'attempt_id': 999999,
            'answers': answers
        }
        
        response = self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)

    def test_submit_with_invalid_question_id(self):
        """Test submission with invalid question ID"""
        response = self.client.get(reverse('onboarding_quiz'))
        attempt_id = response.context['attempt_id']
        
        answers = [
            {'question_id': 999999, 'answer': 'A', 'time_taken': 10}
            for _ in range(10)
        ]
        data = {
            'attempt_id': attempt_id,
            'answers': answers
        }
        
        response = self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)

    def test_results_with_invalid_attempt_id(self):
        """Test results page with invalid attempt ID"""
        url = f"{reverse('onboarding_results')}?attempt=999999"
        response = self.client.get(url)
        
        self.assertRedirects(response, reverse('onboarding_welcome'))

