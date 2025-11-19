"""
Tests for the quiz-based DailyQuestService.

SOFA Refactoring (Sprint 4):
- Avoid Repetition: Using test_helpers to eliminate duplicate setup code
- Single Responsibility: Each test focuses on one service method
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from home.models import (
    DailyQuest,
    DailyQuestQuestion,
    Lesson,
    LessonQuizQuestion,
    UserDailyQuestAttempt,
)
from home.services.daily_quest_service import DailyQuestService

# SOFA: DRY - Import reusable test helpers
from home.tests.test_helpers import (
    create_test_user,
    create_test_daily_quest,
    create_test_daily_quest_attempt
)


class DailyQuestServiceTests(TestCase):
    """Validate quest generation, scoring, and stats."""

    def setUp(self):
        self.user = create_test_user(password='pass1234')  # SOFA: DRY
        self.lesson = Lesson.objects.create(
            title='Colors in Spanish',
            language='Spanish',
            slug='colors-test',
            lesson_type='flashcard',
            xp_value=100,
            is_published=True
        )
        options = ['Rojo', 'Azul', 'Verde', 'Amarillo']
        for idx in range(1, 7):
            LessonQuizQuestion.objects.create(
                lesson=self.lesson,
                question=f'Color question {idx}',
                options=options,
                correct_index=idx % len(options),
                order=idx
            )

    def test_get_today_challenge_creates_quest_with_questions(self):
        """Service should create a quest with exactly 5 stored questions."""
        challenge = DailyQuestService.get_today_challenge(self.user)

        self.assertIsNotNone(challenge)
        quest = challenge['quest']
        self.assertEqual(quest.language, 'Spanish')
        self.assertEqual(quest.questions.count(), DailyQuestService.QUESTIONS_PER_CHALLENGE)

    def test_submit_challenge_records_attempt_and_awards_xp(self):
        """Submitting answers should record attempt stats and award XP."""
        challenge = DailyQuestService.get_today_challenge(self.user)
        questions = challenge['questions']
        post_data = {
            f'question_{question.id}': question.correct_index
            for question in questions
        }

        result = DailyQuestService.submit_challenge(self.user, post_data)

        attempt = UserDailyQuestAttempt.objects.get(user=self.user, daily_quest=challenge['quest'])
        self.assertTrue(attempt.is_completed)
        self.assertEqual(attempt.correct_answers, DailyQuestService.QUESTIONS_PER_CHALLENGE)
        self.assertEqual(result['xp_awarded'], attempt.xp_earned)

    def test_get_weekly_stats_only_counts_recent_attempts(self):
        """Weekly stats should include attempts completed within last 7 days."""
        quest = DailyQuest.objects.create(
            date=timezone.localdate(),
            title='Daily Colors Challenge',
            description='Test quest',
            language='Spanish',
            based_on_lesson=self.lesson,
            quest_type='quiz',
            xp_reward=50
        )
        old_quest = DailyQuest.objects.create(
            date=timezone.localdate() - timedelta(days=10),
            title='Daily Colors Challenge (Old)',
            description='Test quest',
            language='Spanish',
            based_on_lesson=self.lesson,
            quest_type='quiz',
            xp_reward=50
        )
        DailyQuestQuestion.objects.create(
            daily_quest=quest,
            question_text='Dummy',
            options=['A', 'B', 'C', 'D'],
            correct_index=0,
            order=1
        )
        attempt = UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=quest,
            correct_answers=4,
            total_questions=5,
            xp_earned=40,
            is_completed=True,
            completed_at=timezone.now()
        )
        old_attempt = UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=old_quest,
            correct_answers=2,
            total_questions=5,
            xp_earned=20,
            is_completed=True,
            completed_at=timezone.now() - timedelta(days=10)
        )
        old_attempt.save(update_fields=['completed_at'])

        stats = DailyQuestService.get_weekly_stats(self.user)

        self.assertEqual(stats['challenges_completed'], 1)
        self.assertEqual(stats['xp_earned'], attempt.xp_earned)

    def test_get_lifetime_stats_counts_all_attempts(self):
        """Lifetime stats aggregate every completed attempt."""
        recent_quest = DailyQuest.objects.create(
            date=timezone.localdate(),
            title='Daily Colors Challenge',
            description='Test quest',
            language='Spanish',
            based_on_lesson=self.lesson,
            quest_type='quiz',
            xp_reward=50
        )
        old_quest = DailyQuest.objects.create(
            date=timezone.localdate() - timedelta(days=3),
            title='Daily Colors Challenge (Old)',
            description='Test quest',
            language='Spanish',
            based_on_lesson=self.lesson,
            quest_type='quiz',
            xp_reward=50
        )
        UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=recent_quest,
            correct_answers=3,
            total_questions=5,
            xp_earned=30,
            is_completed=True,
            completed_at=timezone.now()
        )
        UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=old_quest,
            correct_answers=5,
            total_questions=5,
            xp_earned=50,
            is_completed=True,
            completed_at=timezone.now() - timedelta(days=30)
        )

        stats = DailyQuestService.get_lifetime_stats(self.user)

        self.assertEqual(stats['challenges_completed'], 2)
        self.assertEqual(stats['xp_earned'], 80)

    def test_user_language_locks_for_day(self):
        """Daily challenge language should lock to first language seen each day."""
        self.user.profile.target_language = 'Spanish'
        self.user.profile.save(update_fields=['target_language'])

        first_challenge = DailyQuestService.get_today_challenge(self.user)
        self.assertEqual(first_challenge['quest'].language, 'Spanish')

        # Change user target language mid-day
        profile = self.user.profile
        profile.target_language = 'French'
        profile.save(update_fields=['target_language'])

        second_challenge = DailyQuestService.get_today_challenge(self.user)
        self.assertEqual(second_challenge['quest'].language, 'Spanish')

        # Simulate next day to allow language change
        profile.daily_challenge_language_date = timezone.localdate() - timedelta(days=1)
        profile.save(update_fields=['daily_challenge_language_date'])
        refreshed = DailyQuestService.get_today_challenge(self.user)
        self.assertEqual(refreshed['quest'].language, 'French')
