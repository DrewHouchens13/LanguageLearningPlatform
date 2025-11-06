"""
Progress tracking view tests.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from home.models import (
    UserProgress, QuizResult, LessonCompletion,
    OnboardingAttempt, OnboardingQuestion
)
import json


class TestOnboardingStatsPopulation(TestCase):
    """Test that onboarding quiz populates progress stats"""

    def setUp(self):
        """Create test user and questions"""
        self.client = Client()
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

    def test_onboarding_populates_quiz_accuracy(self):
        """Onboarding completion creates QuizResult and updates accuracy stats"""
        self.client.login(username='testuser', password='pass123')
        
        # Create attempt
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        # Submit onboarding (all correct)
        answers = [
            {'question_id': q.id, 'answer': 'A', 'time_taken': 10}
            for q in self.questions
        ]
        
        data = {
            'attempt_id': attempt.id,
            'answers': answers
        }
        
        response = self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify QuizResult was created
        quiz_result = QuizResult.objects.filter(user=self.user).first()
        self.assertIsNotNone(quiz_result)
        self.assertEqual(quiz_result.quiz_id, 'onboarding_Spanish')
        self.assertEqual(quiz_result.quiz_title, 'Spanish Placement Assessment')
        self.assertEqual(quiz_result.score, 19)
        self.assertEqual(quiz_result.total_questions, 19)
        
        # Verify UserProgress was updated
        user_progress = UserProgress.objects.get(user=self.user)
        self.assertEqual(user_progress.total_quizzes_taken, 1)
        self.assertEqual(user_progress.overall_quiz_accuracy, 100.0)

    def test_onboarding_populates_minutes_studied(self):
        """Onboarding time is added to total minutes studied"""
        self.client.login(username='testuser', password='pass123')
        
        # Create attempt
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        # Submit with known time (60 seconds per question = 600 seconds = 10 minutes)
        answers = [
            {'question_id': q.id, 'answer': 'A', 'time_taken': 60}
            for q in self.questions
        ]
        
        data = {
            'attempt_id': attempt.id,
            'answers': answers
        }
        
        self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Verify minutes were added
        user_progress = UserProgress.objects.get(user=self.user)
        self.assertEqual(user_progress.total_minutes_studied, 10)

    def test_onboarding_populates_quizzes_taken(self):
        """Onboarding increments total quizzes taken"""
        self.client.login(username='testuser', password='pass123')
        
        # Create attempt
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        # Submit onboarding
        answers = [
            {'question_id': q.id, 'answer': 'A', 'time_taken': 10}
            for q in self.questions
        ]
        
        data = {
            'attempt_id': attempt.id,
            'answers': answers
        }
        
        self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Verify quizzes count
        user_progress = UserProgress.objects.get(user=self.user)
        self.assertEqual(user_progress.total_quizzes_taken, 1)

    def test_onboarding_does_not_count_as_unit(self):
        """Onboarding does not create LessonCompletion or increment units completed"""
        self.client.login(username='testuser', password='pass123')
        
        # Create attempt
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        # Submit onboarding
        answers = [
            {'question_id': q.id, 'answer': 'A', 'time_taken': 10}
            for q in self.questions
        ]
        
        data = {
            'attempt_id': attempt.id,
            'answers': answers
        }
        
        self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Verify no LessonCompletion was created
        lesson_count = LessonCompletion.objects.filter(user=self.user).count()
        self.assertEqual(lesson_count, 0)
        
        # Verify units completed is 0
        user_progress = UserProgress.objects.get(user=self.user)
        self.assertEqual(user_progress.total_lessons_completed, 0)

    def test_weekly_stats_include_recent_onboarding(self):
        """Onboarding quiz accuracy shows in weekly stats"""
        self.client.login(username='testuser', password='pass123')
        
        # Create attempt
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        # Submit onboarding (120 seconds total = 2 minutes)
        answers = [
            {'question_id': q.id, 'answer': 'A', 'time_taken': 12}
            for q in self.questions
        ]
        
        data = {
            'attempt_id': attempt.id,
            'answers': answers
        }
        
        self.client.post(
            reverse('submit_onboarding'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Get weekly stats
        user_progress = UserProgress.objects.get(user=self.user)
        weekly_stats = user_progress.get_weekly_stats()
        
        # Verify onboarding quiz accuracy is included in weekly stats
        # Note: Minutes come from LessonCompletion, but quiz accuracy comes from QuizResult
        self.assertEqual(weekly_stats['weekly_accuracy'], 100.0)
        
        # Minutes are tracked in total_minutes_studied, not weekly_minutes (which is from lessons)
        self.assertEqual(user_progress.total_minutes_studied, 2)

    def test_lifetime_stats_include_old_onboarding(self):
        """Onboarding completed >7 days ago only in lifetime stats"""
        self.client.login(username='testuser', password='pass123')
        
        # Create QuizResult from 10 days ago
        old_quiz = QuizResult.objects.create(
            user=self.user,
            quiz_id='onboarding_Spanish',
            quiz_title='Spanish Placement Assessment',
            score=15,
            total_questions=19
        )
        # Manually set created date to 10 days ago
        old_date = timezone.now() - timedelta(days=10)
        QuizResult.objects.filter(id=old_quiz.id).update(completed_at=old_date)
        
        # Create UserProgress with stats
        user_progress = UserProgress.objects.create(
            user=self.user,
            total_minutes_studied=5,
            total_quizzes_taken=1,
            total_lessons_completed=0,
            overall_quiz_accuracy=78.9
        )
        
        # Get weekly stats
        weekly_stats = user_progress.get_weekly_stats()
        
        # Verify old onboarding NOT in weekly stats
        self.assertEqual(weekly_stats['weekly_minutes'], 0)
        self.assertEqual(weekly_stats['weekly_accuracy'], 0.0)
        
        # Verify old onboarding IS in lifetime stats
        self.assertEqual(user_progress.total_quizzes_taken, 1)
        self.assertEqual(user_progress.overall_quiz_accuracy, 78.9)
