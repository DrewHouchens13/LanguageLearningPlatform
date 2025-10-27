"""
Model tests for all app models.
Tests core models (UserProgress, LessonCompletion, QuizResult) and
onboarding models (UserProfile, OnboardingQuestion, OnboardingAttempt, OnboardingAnswer).
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import IntegrityError
from datetime import timedelta

from home.models import (
    UserProgress, LessonCompletion, QuizResult,
    UserProfile, OnboardingQuestion, OnboardingAttempt, OnboardingAnswer
)


# =============================================================================
# CORE MODEL TESTS
# =============================================================================

class UserProgressModelTest(TestCase):
    """Test UserProgress model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        self.progress = UserProgress.objects.create(user=self.user)
    
    def test_defaults(self):
        """Test default values"""
        self.assertEqual(self.progress.total_minutes_studied, 0)
        self.assertEqual(self.progress.total_lessons_completed, 0)
        self.assertEqual(self.progress.total_quizzes_taken, 0)
        self.assertEqual(self.progress.overall_quiz_accuracy, 0.0)
    
    def test_calculate_quiz_accuracy(self):
        """Test quiz accuracy calculation"""
        QuizResult.objects.create(user=self.user, quiz_id='q1', score=8, total_questions=10)
        QuizResult.objects.create(user=self.user, quiz_id='q2', score=15, total_questions=20)
        accuracy = self.progress.calculate_quiz_accuracy()
        self.assertEqual(accuracy, 76.7)  # 23/30
    
    def test_get_weekly_stats(self):
        """Test weekly statistics calculation"""
        LessonCompletion.objects.create(user=self.user, lesson_id='l1', duration_minutes=30)
        LessonCompletion.objects.create(user=self.user, lesson_id='l2', duration_minutes=45)
        QuizResult.objects.create(user=self.user, quiz_id='q1', score=9, total_questions=10)
        
        stats = self.progress.get_weekly_stats()
        self.assertEqual(stats['weekly_minutes'], 75)
        self.assertEqual(stats['weekly_lessons'], 2)
        self.assertEqual(stats['weekly_accuracy'], 90.0)


class LessonCompletionModelTest(TestCase):
    """Test LessonCompletion model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
    
    def test_creation_and_ordering(self):
        """Test lesson creation and ordering (most recent first)"""
        l1 = LessonCompletion.objects.create(user=self.user, lesson_id='l1', duration_minutes=20)
        l2 = LessonCompletion.objects.create(user=self.user, lesson_id='l2', duration_minutes=30)
        
        lessons = LessonCompletion.objects.all()
        self.assertEqual(lessons[0], l2)  # Most recent first


class QuizResultModelTest(TestCase):
    """Test QuizResult model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
    
    def test_accuracy_percentage(self):
        """Test accuracy percentage property"""
        quiz = QuizResult.objects.create(user=self.user, quiz_id='q1', score=17, total_questions=20)
        self.assertEqual(quiz.accuracy_percentage, 85.0)
    
    def test_accuracy_percentage_zero_division(self):
        """Test accuracy handles zero total_questions"""
        quiz = QuizResult.objects.create(user=self.user, quiz_id='q1', score=0, total_questions=0)
        self.assertEqual(quiz.accuracy_percentage, 0.0)


# =============================================================================
# ONBOARDING MODEL TESTS
# =============================================================================

class UserProfileModelTest(TestCase):
    """Test UserProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
    
    def test_defaults(self):
        """Test default values"""
        profile = UserProfile.objects.create(user=self.user)
        self.assertIsNone(profile.proficiency_level)
        self.assertFalse(profile.has_completed_onboarding)
        self.assertEqual(profile.target_language, 'Spanish')
        self.assertEqual(profile.daily_goal_minutes, 15)
    
    def test_with_onboarding_complete(self):
        """Test profile with completed onboarding"""
        profile = UserProfile.objects.create(
            user=self.user,
            proficiency_level='A2',
            has_completed_onboarding=True,
            onboarding_completed_at=timezone.now()
        )
        self.assertEqual(profile.proficiency_level, 'A2')
        self.assertTrue(profile.has_completed_onboarding)
    
    def test_one_to_one_constraint(self):
        """Test only one profile per user"""
        UserProfile.objects.create(user=self.user)
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(user=self.user)


class OnboardingQuestionModelTest(TestCase):
    """Test OnboardingQuestion model"""
    
    def test_creation(self):
        """Test question creation"""
        q = OnboardingQuestion.objects.create(
            question_number=1,
            question_text='Test question?',
            language='Spanish',
            difficulty_level='A1',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='B',
            difficulty_points=1
        )
        self.assertEqual(q.question_number, 1)
        self.assertEqual(q.correct_answer, 'B')
    
    def test_unique_constraint(self):
        """Test (language, question_number) uniqueness"""
        OnboardingQuestion.objects.create(
            question_number=1, question_text='Q1', language='Spanish',
            difficulty_level='A1', option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A', difficulty_points=1
        )
        with self.assertRaises(IntegrityError):
            OnboardingQuestion.objects.create(
                question_number=1, question_text='Q1 duplicate', language='Spanish',
                difficulty_level='A1', option_a='A', option_b='B', option_c='C', option_d='D',
                correct_answer='A', difficulty_points=1
            )


class OnboardingAttemptModelTest(TestCase):
    """Test OnboardingAttempt model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
    
    def test_authenticated_user_attempt(self):
        """Test attempt for authenticated user"""
        attempt = OnboardingAttempt.objects.create(user=self.user, language='Spanish')
        self.assertEqual(attempt.user, self.user)
        self.assertIsNotNone(attempt.started_at)
    
    def test_guest_attempt(self):
        """Test attempt for guest user"""
        attempt = OnboardingAttempt.objects.create(session_key='abc123', language='Spanish')
        self.assertIsNone(attempt.user)
        self.assertEqual(attempt.session_key, 'abc123')
    
    def test_score_percentage(self):
        """Test score percentage calculation"""
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish',
            total_score=12,
            total_possible=19
        )
        self.assertEqual(attempt.score_percentage, 63.2)


class OnboardingAnswerModelTest(TestCase):
    """Test OnboardingAnswer model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='pass123')
        self.question = OnboardingQuestion.objects.create(
            question_number=1, question_text='Test?', language='Spanish',
            difficulty_level='A1', option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='B', difficulty_points=1
        )
        self.attempt = OnboardingAttempt.objects.create(user=self.user, language='Spanish')
    
    def test_answer_creation(self):
        """Test answer creation and relationship"""
        answer = OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            user_answer='B',
            is_correct=True,
            time_taken_seconds=15
        )
        self.assertEqual(answer.user_answer, 'B')
        self.assertTrue(answer.is_correct)
        self.assertEqual(self.attempt.answers.count(), 1)
