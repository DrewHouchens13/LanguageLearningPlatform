from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import IntegrityError
from home.models import (
    UserProfile, OnboardingQuestion, OnboardingAttempt, OnboardingAnswer
)


class TestUserProfileModel(TestCase):
    """Test UserProfile model functionality"""

    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_user_profile_creation_with_defaults(self):
        """Test UserProfile is created with correct default values"""
        profile = UserProfile.objects.create(user=self.user)
        
        self.assertEqual(profile.user, self.user)
        self.assertIsNone(profile.proficiency_level)
        self.assertFalse(profile.has_completed_onboarding)
        self.assertIsNone(profile.onboarding_completed_at)
        self.assertEqual(profile.target_language, 'Spanish')
        self.assertEqual(profile.daily_goal_minutes, 15)
        self.assertEqual(profile.learning_motivation, '')
        self.assertIsNotNone(profile.created_at)
        self.assertIsNotNone(profile.updated_at)

    def test_user_profile_with_onboarding_complete(self):
        """Test UserProfile with completed onboarding"""
        completed_time = timezone.now()
        profile = UserProfile.objects.create(
            user=self.user,
            proficiency_level='A2',
            has_completed_onboarding=True,
            onboarding_completed_at=completed_time,
            target_language='Spanish',
            daily_goal_minutes=30,
            learning_motivation='Want to travel to Spain'
        )
        
        self.assertEqual(profile.proficiency_level, 'A2')
        self.assertTrue(profile.has_completed_onboarding)
        self.assertEqual(profile.onboarding_completed_at, completed_time)
        self.assertEqual(profile.daily_goal_minutes, 30)
        self.assertEqual(profile.learning_motivation, 'Want to travel to Spain')

    def test_user_profile_string_representation(self):
        """Test __str__ method returns correct format"""
        profile = UserProfile.objects.create(
            user=self.user,
            proficiency_level='A1'
        )
        expected = f"{self.user.username}'s Profile - Beginner (A1)"
        self.assertEqual(str(profile), expected)

    def test_user_profile_string_representation_without_level(self):
        """Test __str__ method for profile without proficiency level"""
        profile = UserProfile.objects.create(user=self.user)
        expected = f"{self.user.username}'s Profile - Not assessed"
        self.assertEqual(str(profile), expected)

    def test_user_profile_one_to_one_relationship(self):
        """Test OneToOne relationship with User"""
        profile = UserProfile.objects.create(
            user=self.user,
            proficiency_level='B1'
        )
        
        # Access profile from user
        self.assertEqual(self.user.language_profile, profile)

    def test_user_profile_unique_constraint(self):
        """Test that only one profile per user can exist"""
        UserProfile.objects.create(user=self.user)
        
        # Attempting to create second profile should raise error
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(user=self.user)

    def test_user_profile_proficiency_level_choices(self):
        """Test proficiency level choices"""
        valid_levels = ['A1', 'A2', 'B1']
        
        for level in valid_levels:
            profile = UserProfile.objects.create(
                user=User.objects.create_user(
                    username=f'user_{level}',
                    email=f'{level}@example.com'
                ),
                proficiency_level=level
            )
            self.assertEqual(profile.proficiency_level, level)


class TestOnboardingQuestionModel(TestCase):
    """Test OnboardingQuestion model functionality"""

    def test_onboarding_question_creation(self):
        """Test OnboardingQuestion is created with correct fields"""
        question = OnboardingQuestion.objects.create(
            question_number=1,
            question_text='What is the Spanish word for "hello"?',
            language='Spanish',
            difficulty_level='A1',
            option_a='Adiós',
            option_b='Hola',
            option_c='Gracias',
            option_d='Por favor',
            correct_answer='B',
            explanation='Hola is the most common greeting in Spanish.',
            difficulty_points=1
        )
        
        self.assertEqual(question.question_number, 1)
        self.assertEqual(question.question_text, 'What is the Spanish word for "hello"?')
        self.assertEqual(question.language, 'Spanish')
        self.assertEqual(question.difficulty_level, 'A1')
        self.assertEqual(question.option_b, 'Hola')
        self.assertEqual(question.correct_answer, 'B')
        self.assertEqual(question.difficulty_points, 1)

    def test_onboarding_question_string_representation(self):
        """Test __str__ method returns correct format"""
        question = OnboardingQuestion.objects.create(
            question_number=1,
            question_text='What is the Spanish word for "hello"?',
            language='Spanish',
            difficulty_level='A1',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='B'
        )
        
        expected = 'Q1 (Spanish - A1): What is the Spanish word for "hello"?...'
        self.assertEqual(str(question), expected)

    def test_onboarding_question_unique_constraint(self):
        """Test (language, question_number) unique constraint"""
        OnboardingQuestion.objects.create(
            question_number=1,
            question_text='First question',
            language='Spanish',
            difficulty_level='A1',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A'
        )
        
        # Attempting to create duplicate should raise error
        with self.assertRaises(IntegrityError):
            OnboardingQuestion.objects.create(
                question_number=1,
                question_text='Different question',
                language='Spanish',
                difficulty_level='A2',
                option_a='A', option_b='B', option_c='C', option_d='D',
                correct_answer='B'
            )

    def test_onboarding_question_different_languages_same_number(self):
        """Test same question number allowed for different languages"""
        OnboardingQuestion.objects.create(
            question_number=1,
            question_text='Spanish question',
            language='Spanish',
            difficulty_level='A1',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A'
        )
        
        # Should allow same question_number for different language
        french_question = OnboardingQuestion.objects.create(
            question_number=1,
            question_text='French question',
            language='French',
            difficulty_level='A1',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A'
        )
        
        self.assertIsNotNone(french_question)

    def test_onboarding_question_ordering(self):
        """Test questions are ordered by language then question_number"""
        OnboardingQuestion.objects.create(
            question_number=2, question_text='Q2', language='Spanish',
            difficulty_level='A1', option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A'
        )
        OnboardingQuestion.objects.create(
            question_number=1, question_text='Q1', language='Spanish',
            difficulty_level='A1', option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A'
        )
        
        questions = OnboardingQuestion.objects.filter(language='Spanish')
        self.assertEqual(questions[0].question_number, 1)
        self.assertEqual(questions[1].question_number, 2)


class TestOnboardingAttemptModel(TestCase):
    """Test OnboardingAttempt model functionality"""

    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_onboarding_attempt_creation_authenticated(self):
        """Test OnboardingAttempt creation for authenticated user"""
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        self.assertEqual(attempt.user, self.user)
        self.assertEqual(attempt.language, 'Spanish')
        self.assertIsNotNone(attempt.started_at)
        self.assertIsNone(attempt.completed_at)
        self.assertEqual(attempt.calculated_level, '')
        self.assertEqual(attempt.total_score, 0)
        self.assertEqual(attempt.total_possible, 0)

    def test_onboarding_attempt_creation_guest(self):
        """Test OnboardingAttempt creation for guest user"""
        attempt = OnboardingAttempt.objects.create(
            session_key='abc123xyz789',
            language='Spanish'
        )
        
        self.assertIsNone(attempt.user)
        self.assertEqual(attempt.session_key, 'abc123xyz789')

    def test_onboarding_attempt_with_results(self):
        """Test OnboardingAttempt with completed results"""
        completed_time = timezone.now()
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish',
            calculated_level='A2',
            total_score=12,
            total_possible=19,
            completed_at=completed_time
        )
        
        self.assertEqual(attempt.calculated_level, 'A2')
        self.assertEqual(attempt.total_score, 12)
        self.assertEqual(attempt.total_possible, 19)
        self.assertEqual(attempt.completed_at, completed_time)

    def test_onboarding_attempt_score_percentage(self):
        """Test score_percentage property calculation"""
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish',
            calculated_level='A2',
            total_score=12,
            total_possible=19
        )
        
        # 12/19 = 63.15... rounded to 63.2
        self.assertEqual(attempt.score_percentage, 63.2)

    def test_onboarding_attempt_score_percentage_zero_total(self):
        """Test score_percentage handles zero total_possible"""
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        self.assertEqual(attempt.score_percentage, 0.0)

    def test_onboarding_attempt_string_representation_authenticated(self):
        """Test __str__ method for authenticated user"""
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish',
            calculated_level='A2'
        )
        
        expected = f"{self.user.username} - Spanish (A2)"
        self.assertEqual(str(attempt), expected)

    def test_onboarding_attempt_string_representation_guest(self):
        """Test __str__ method for guest user"""
        attempt = OnboardingAttempt.objects.create(
            session_key='abc123xyz789',
            language='Spanish',
            calculated_level='A1'
        )
        
        expected = "Guest-abc123xy - Spanish (A1)"
        self.assertEqual(str(attempt), expected)

    def test_onboarding_attempt_string_representation_in_progress(self):
        """Test __str__ method for in-progress attempt"""
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        expected = f"{self.user.username} - Spanish (In Progress)"
        self.assertEqual(str(attempt), expected)

    def test_onboarding_attempt_ordering(self):
        """Test attempts are ordered by most recent first"""
        attempt1 = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        attempt2 = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        attempts = OnboardingAttempt.objects.all()
        self.assertEqual(attempts[0], attempt2)
        self.assertEqual(attempts[1], attempt1)


class TestOnboardingAnswerModel(TestCase):
    """Test OnboardingAnswer model functionality"""

    def setUp(self):
        """Create test user, question, and attempt"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.question = OnboardingQuestion.objects.create(
            question_number=1,
            question_text='What is the Spanish word for "hello"?',
            language='Spanish',
            difficulty_level='A1',
            option_a='Adiós',
            option_b='Hola',
            option_c='Gracias',
            option_d='Por favor',
            correct_answer='B',
            difficulty_points=1
        )
        self.attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )

    def test_onboarding_answer_creation_correct(self):
        """Test OnboardingAnswer creation with correct answer"""
        answer = OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            user_answer='B',
            is_correct=True,
            time_taken_seconds=15
        )
        
        self.assertEqual(answer.attempt, self.attempt)
        self.assertEqual(answer.question, self.question)
        self.assertEqual(answer.user_answer, 'B')
        self.assertTrue(answer.is_correct)
        self.assertEqual(answer.time_taken_seconds, 15)
        self.assertIsNotNone(answer.answered_at)

    def test_onboarding_answer_creation_incorrect(self):
        """Test OnboardingAnswer creation with incorrect answer"""
        answer = OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            user_answer='A',
            is_correct=False,
            time_taken_seconds=10
        )
        
        self.assertEqual(answer.user_answer, 'A')
        self.assertFalse(answer.is_correct)

    def test_onboarding_answer_string_representation_correct(self):
        """Test __str__ method for correct answer"""
        answer = OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            user_answer='B',
            is_correct=True
        )
        
        expected = "✓ Q1 - B"
        self.assertEqual(str(answer), expected)

    def test_onboarding_answer_string_representation_incorrect(self):
        """Test __str__ method for incorrect answer"""
        answer = OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            user_answer='A',
            is_correct=False
        )
        
        expected = "✗ Q1 - A"
        self.assertEqual(str(answer), expected)

    def test_onboarding_answer_related_name(self):
        """Test related_name for answers on attempt"""
        OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            user_answer='B',
            is_correct=True
        )
        
        self.assertEqual(self.attempt.answers.count(), 1)
        self.assertEqual(self.attempt.answers.first().user_answer, 'B')

    def test_onboarding_answer_ordering(self):
        """Test answers are ordered by question number"""
        question2 = OnboardingQuestion.objects.create(
            question_number=2,
            question_text='Second question',
            language='Spanish',
            difficulty_level='A1',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A',
            difficulty_points=1
        )
        
        answer2 = OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=question2,
            user_answer='A',
            is_correct=True
        )
        answer1 = OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            user_answer='B',
            is_correct=True
        )
        
        answers = self.attempt.answers.all()
        self.assertEqual(answers[0].question.question_number, 1)
        self.assertEqual(answers[1].question.question_number, 2)

    def test_onboarding_answer_cascade_delete_on_attempt(self):
        """Test answers are deleted when attempt is deleted"""
        OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            user_answer='B',
            is_correct=True
        )
        
        attempt_id = self.attempt.id
        self.attempt.delete()
        
        # Answers should be deleted
        self.assertEqual(
            OnboardingAnswer.objects.filter(attempt_id=attempt_id).count(),
            0
        )

