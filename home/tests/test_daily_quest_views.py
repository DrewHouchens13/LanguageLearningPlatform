"""
Unit tests for the Daily Challenge views.

SOFA Refactoring (Sprint 4):
- Avoid Repetition: Using test_helpers to eliminate duplicate setup code
"""
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from home.models import DailyQuest, Lesson, LessonQuizQuestion, UserDailyQuestAttempt

# SOFA: DRY - Import reusable test helpers
from home.tests.test_helpers import (
    create_test_user,
    create_test_daily_quest,
    create_test_daily_quest_attempt
)


class DailyChallengeViewTests(TestCase):
    """Validate the daily challenge page and submissions."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass1234'
        )
        self.lesson = Lesson.objects.create(
            title='Colors',
            language='Spanish',
            slug='colors-test',
            xp_value=100,
            is_published=True
        )
        LessonQuizQuestion.objects.create(
            lesson=self.lesson,
            question='What is red?',
            options=['Rojo', 'Azul', 'Verde', 'Amarillo'],
            correct_index=0,
            order=1
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
        quest = SimpleNamespace(
            date=date(2025, 11, 16),
            language='Spanish',
            based_on_lesson=SimpleNamespace(title='Colors in Spanish')
        )
        mock_today.return_value = {
            'quest': quest,
            'attempt': None,
            'questions': [],
            'language_metadata': {'flag': '🇪🇸', 'native_name': 'Español'},
            'is_completed': False,
            'xp_reward': 75,
        }
        mock_weekly.return_value = {'challenges_completed': 0, 'xp_earned': 0, 'accuracy': 0}
        mock_lifetime.return_value = {'challenges_completed': 0, 'xp_earned': 0, 'accuracy': 0}

        response = self.client.get(reverse('daily_quest'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Daily Challenge')
        self.assertIn('challenge', response.context)

    @patch('home.views.DailyQuestService.get_lifetime_stats')
    @patch('home.views.DailyQuestService.get_weekly_stats')
    @patch('home.views.DailyQuestService.get_today_challenge')
    def test_daily_challenge_view_shows_completion_state(self, mock_today, mock_weekly, mock_lifetime):
        self.client.login(username='testuser', password='pass1234')
        quest = SimpleNamespace(
            date=date(2025, 11, 16),
            language='Spanish',
            based_on_lesson=SimpleNamespace(title='Colors in Spanish')
        )
        attempt = SimpleNamespace(correct_answers=5, total_questions=5, xp_earned=75)
        mock_today.return_value = {
            'quest': quest,
            'attempt': attempt,
            'questions': [],
            'language_metadata': {'flag': '🇪🇸', 'native_name': 'Español'},
            'is_completed': True,
            'xp_reward': 75,
        }
        mock_weekly.return_value = {'challenges_completed': 1, 'xp_earned': 75, 'accuracy': 100}
        mock_lifetime.return_value = {'challenges_completed': 10, 'xp_earned': 750, 'accuracy': 90}

        response = self.client.get(reverse('daily_quest'))

        self.assertContains(response, 'Challenge Completed')

    @patch('home.views.DailyQuestService.submit_challenge')
    def test_daily_challenge_submit_handles_post(self, mock_submit):
        self.client.login(username='testuser', password='pass1234')
        mock_submit.return_value = {'correct': 5, 'total': 5, 'xp_awarded': 75}

        response = self.client.post(reverse('daily_quest_submit'), {'question_1': '0'})

        self.assertRedirects(response, reverse('daily_quest'))
        mock_submit.assert_called_once()


class QuestHistoryViewTests(TestCase):
    """Ensure quest history reflects UserDailyQuestAttempt entries."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass1234'
        )
        self.lesson = Lesson.objects.create(
            title='Shapes',
            language='Spanish',
            slug='shapes-test',
            xp_value=100,
            is_published=True
        )

    def test_history_requires_authentication(self):
        response = self.client.get(reverse('quest_history'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_history_lists_completed_challenges(self):
        quest = DailyQuest.objects.create(
            date=date(2025, 11, 16),
            title='Shapes Challenge',
            description='Test quest',
            language='Spanish',
            based_on_lesson=self.lesson,
            quest_type='quiz',
            xp_reward=50
        )
        UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=quest,
            correct_answers=4,
            total_questions=5,
            xp_earned=40,
            is_completed=True,
            completed_at=timezone.now()
        )
        self.client.login(username='testuser', password='pass1234')

        response = self.client.get(reverse('quest_history'))

        self.assertEqual(response.status_code, 200)
        attempts = response.context['attempts']
        self.assertEqual(attempts.count(), 1)
        self.assertContains(response, '40 XP')

    def test_history_empty_state(self):
        other_user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='pass1234'
        )
        self.client.login(username=other_user.username, password='pass1234')

        response = self.client.get(reverse('quest_history'))

        self.assertEqual(response.status_code, 200)
        attempts = response.context['attempts']
        self.assertEqual(attempts.count(), 0)
