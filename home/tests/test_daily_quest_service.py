"""
Tests for the revamped DailyQuestService interaction-based challenge system.
"""
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from home.language_registry import get_supported_languages
from home.models import DailyChallengeLog, UserLanguageProfile, UserProfile
from home.services.daily_quest_service import DailyQuestService


class DailyChallengeServiceTests(TestCase):
    """Validate the new onboarding/lesson daily challenge service."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass1234'
        )
        self.profile = UserProfile.objects.get(user=self.user)

    @patch('home.services.daily_quest_service.DailyQuestService._deterministic_choice')
    @patch('home.services.daily_quest_service.timezone.localdate')
    def test_get_today_challenge_can_assign_onboarding(self, mock_date, mock_choice):
        """When pending languages exist, an onboarding task can be assigned."""
        mock_date.return_value = date(2025, 11, 16)
        mock_choice.side_effect = lambda seq, key: seq[-1]  # Prefer onboarding candidate

        challenge = DailyQuestService.get_today_challenge(self.user)

        self.assertEqual(challenge['challenge_type'], 'onboarding')
        self.assertIsNone(challenge['secondary_action'])
        action = challenge['primary_action']
        self.assertIn('Complete onboarding for', action['label'])
        self.assertIn(action['language'], action['label'])

    @patch('home.services.daily_quest_service.DailyQuestService._deterministic_choice')
    @patch('home.services.daily_quest_service.timezone.localdate')
    def test_get_today_challenge_defaults_to_lesson_without_pending_languages(self, mock_date, mock_choice):
        """If every language is onboarded, challenge falls back to a lesson task."""
        mock_date.return_value = date(2025, 11, 17)
        mock_choice.side_effect = lambda seq, key: seq[0]

        for entry in get_supported_languages():
            UserLanguageProfile.objects.update_or_create(
                user=self.user,
                language=entry['name'],
                defaults={'has_completed_onboarding': True}
            )

        challenge = DailyQuestService.get_today_challenge(self.user)

        self.assertEqual(challenge['challenge_type'], 'lesson')
        action = challenge['primary_action']
        self.assertIn('Complete a', action['label'])
        self.assertIn('lessons', action['cta_url'])

    def test_handle_lesson_completion_creates_log_and_awards_xp(self):
        """Completing a lesson should create a log entry and grant XP."""
        result = DailyQuestService.handle_lesson_completion(
            self.user,
            language='Spanish',
            lesson_title='Greetings'
        )

        self.assertTrue(result['completed'])
        log = DailyChallengeLog.objects.get(user=self.user)
        self.assertEqual(log.completed_via, 'lesson')
        self.assertEqual(log.language, 'Spanish')
        self.user.profile.refresh_from_db()
        self.assertGreater(self.user.profile.total_xp, 0)

    def test_handle_onboarding_completion_creates_log(self):
        """Completing onboarding should log the challenge."""
        result = DailyQuestService.handle_onboarding_completion(
            self.user,
            language='French'
        )

        self.assertTrue(result['completed'])
        log = DailyChallengeLog.objects.get(user=self.user)
        self.assertEqual(log.completed_via, 'onboarding')
        self.assertEqual(log.language, 'French')

    def test_get_weekly_stats_counts_recent_logs(self):
        """Weekly stats should sum only recent challenge completions."""
        today = date.today()
        DailyChallengeLog.objects.create(
            user=self.user,
            date=today,
            completed_via='lesson',
            language='Spanish',
            xp_awarded=75
        )
        DailyChallengeLog.objects.create(
            user=self.user,
            date=today - timedelta(days=10),
            completed_via='onboarding',
            language='French',
            xp_awarded=75
        )

        stats = DailyQuestService.get_weekly_stats(self.user)

        self.assertEqual(stats['challenges_completed'], 1)
        self.assertEqual(stats['xp_earned'], 75)

    def test_get_lifetime_stats_sums_all_logs(self):
        """Lifetime stats should aggregate every logged completion."""
        for offset in range(3):
            DailyChallengeLog.objects.create(
                user=self.user,
                date=date.today() - timedelta(days=offset),
                completed_via='lesson',
                language='Spanish',
                xp_awarded=75
            )

        stats = DailyQuestService.get_lifetime_stats(self.user)

        self.assertEqual(stats['challenges_completed'], 3)
        self.assertEqual(stats['xp_earned'], 225)
