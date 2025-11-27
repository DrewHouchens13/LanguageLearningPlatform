"""
Progress tracking view tests.

SOFA Refactoring (Sprint 4):
- Avoid Repetition: Using test_helpers to eliminate duplicate setup code
- Single Responsibility: Each test focuses on one aspect
"""

import json
from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from home.models import LessonCompletion, QuizResult, UserProgress
# SOFA: DRY - Import reusable test helpers
from home.tests.test_helpers import (create_test_onboarding_attempt,
                                     create_test_onboarding_questions,
                                     create_test_user,
                                     submit_onboarding_answers)


class TestOnboardingStatsPopulation(TestCase):
    """Test that onboarding quiz populates progress stats"""

    def setUp(self):
        """Create test user and questions (SOFA: Using helpers to avoid duplication)"""
        self.client = Client()
        self.user = create_test_user()  # SOFA: Single Responsibility helper
        self.questions = create_test_onboarding_questions()  # SOFA: DRY principle

    def test_onboarding_populates_quiz_accuracy(self):
        """Onboarding completion creates QuizResult and updates accuracy stats"""
        self.client.login(username='testuser', password='pass123')

        # SOFA: DRY - Use helper to avoid duplicate attempt creation
        attempt = create_test_onboarding_attempt(self.user)

        # SOFA: DRY - Use helper to avoid duplicate submission logic
        response = submit_onboarding_answers(self.client, attempt, self.questions)

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

        # SOFA: DRY - Use helper for attempt creation
        attempt = create_test_onboarding_attempt(self.user)

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

        # SOFA: DRY - Use helpers to eliminate duplicate setup/submission code
        attempt = create_test_onboarding_attempt(self.user)
        submit_onboarding_answers(self.client, attempt, self.questions)
        
        # Verify quizzes count
        user_progress = UserProgress.objects.get(user=self.user)
        self.assertEqual(user_progress.total_quizzes_taken, 1)

    def test_onboarding_does_not_count_as_unit(self):
        """Onboarding does not create LessonCompletion or increment units completed"""
        self.client.login(username='testuser', password='pass123')

        # SOFA: DRY - Use helpers to eliminate duplicate setup/submission code
        attempt = create_test_onboarding_attempt(self.user)
        submit_onboarding_answers(self.client, attempt, self.questions)
        
        # Verify no LessonCompletion was created
        lesson_count = LessonCompletion.objects.filter(user=self.user).count()
        self.assertEqual(lesson_count, 0)
        
        # Verify units completed is 0
        user_progress = UserProgress.objects.get(user=self.user)
        self.assertEqual(user_progress.total_lessons_completed, 0)

    def test_weekly_stats_include_recent_onboarding(self):
        """Onboarding quiz accuracy shows in weekly stats"""
        self.client.login(username='testuser', password='pass123')

        # SOFA: DRY - Use helper for attempt creation
        attempt = create_test_onboarding_attempt(self.user)

        # Submit onboarding (120 seconds total = 2 minutes) - custom time_taken
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
