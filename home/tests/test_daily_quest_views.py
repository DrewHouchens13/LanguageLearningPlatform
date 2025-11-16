"""
Unit tests for the modern Daily Challenge views.
"""
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from home.models import DailyChallengeLog


class DailyChallengeViewTests(TestCase):
    """Validate the dashboard daily challenge endpoint."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass1234'
        )

    def test_daily_challenge_view_requires_authentication(self):
        response = self.client.get(reverse('daily_quest'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    @patch('home.views.DailyQuestService.get_lifetime_stats')
    @patch('home.views.DailyQuestService.get_weekly_stats')
    @patch('home.views.DailyQuestService.get_today_challenge')
    def test_daily_challenge_view_renders_card(self, mock_today, mock_weekly, mock_lifetime):
        self.client.login(username='testuser', password='pass1234')
        mock_today.return_value = {
            'date': date(2025, 11, 16),
            'completed': False,
            'completed_via': None,
            'xp_reward': 75,
            'challenge_type': 'lesson',
            'pending_languages': [],
            'target_language': 'Spanish',
            'primary_action': {
                'type': 'lesson',
                'label': 'Complete a Spanish lesson',
                'description': 'Finish any lesson in your current language.',
                'cta_label': 'Browse lessons',
                'cta_url': '/lessons/spanish/',
                'icon': '📘',
            },
            'secondary_action': None,
            'log': None,
        }
        mock_weekly.return_value = {'challenges_completed': 0, 'xp_earned': 0}
        mock_lifetime.return_value = {'challenges_completed': 0, 'xp_earned': 0}

        response = self.client.get(reverse('daily_quest'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Today's Daily Challenge")
        self.assertIn('challenge', response.context)

    @patch('home.views.DailyQuestService.get_lifetime_stats')
    @patch('home.views.DailyQuestService.get_weekly_stats')
    @patch('home.views.DailyQuestService.get_today_challenge')
    def test_daily_challenge_view_shows_completion_state(self, mock_today, mock_weekly, mock_lifetime):
        self.client.login(username='testuser', password='pass1234')
        mock_today.return_value = {
            'date': date(2025, 11, 16),
            'completed': True,
            'completed_via': 'lesson',
            'xp_reward': 75,
            'challenge_type': 'lesson',
            'pending_languages': [],
            'target_language': 'Spanish',
            'primary_action': {
                'type': 'lesson',
                'label': 'Complete a Spanish lesson',
                'description': 'Finish any lesson.',
                'cta_label': 'Browse lessons',
                'cta_url': '/lessons/spanish/',
                'icon': '📘',
            },
            'secondary_action': None,
            'log': None,
        }
        mock_weekly.return_value = {'challenges_completed': 1, 'xp_earned': 75}
        mock_lifetime.return_value = {'challenges_completed': 10, 'xp_earned': 750}

        response = self.client.get(reverse('daily_quest'))

        self.assertContains(response, 'Challenge Completed')


class DailyChallengeSubmitViewTests(TestCase):
    """Legacy submit endpoint still needs to gate auth + POST."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass1234'
        )

    def test_submit_requires_authentication(self):
        response = self.client.post(reverse('daily_quest_submit'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_submit_redirects_authenticated_users(self):
        self.client.login(username='testuser', password='pass1234')
        response = self.client.post(reverse('daily_quest_submit'))
        self.assertRedirects(response, reverse('daily_quest'))


class QuestHistoryViewTests(TestCase):
    """Ensure quest history reflects DailyChallengeLog entries."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass1234'
        )

    def test_history_requires_authentication(self):
        response = self.client.get(reverse('quest_history'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_history_lists_completed_challenges(self):
        self.client.login(username='testuser', password='pass1234')
        for offset in range(3):
            DailyChallengeLog.objects.create(
                user=self.user,
                date=date.today() - timedelta(days=offset),
                completed_via='lesson',
                language='Spanish',
                xp_awarded=75
            )

        response = self.client.get(reverse('quest_history'))

        self.assertEqual(response.status_code, 200)
        logs = response.context['logs']
        self.assertEqual(logs.count(), 3)
        self.assertContains(response, '75 XP')

    def test_history_empty_state(self):
        other_user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='pass1234'
        )
        self.client.login(username=other_user.username, password='pass1234')

        response = self.client.get(reverse('quest_history'))

        self.assertEqual(response.status_code, 200)
        logs = response.context['logs']
        self.assertEqual(logs.count(), 0)
