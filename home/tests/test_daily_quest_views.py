"""
Unit tests for Daily Quest views.
Following TDD - write tests first, then implement views.
"""
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from home.models import Lesson, DailyQuest, UserDailyQuestAttempt


class TestDailyQuestView(TestCase):
    """Test daily_quest_view"""

    def setUp(self):
        """Create test user and quest"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create lesson with flashcards
        self.lesson = Lesson.objects.create(
            title='Colors',
            slug='colors',
            lesson_type='flashcard',
            xp_value=100,
            is_published=True
        )
        for i in range(5):
            Flashcard.objects.create(
                lesson=self.lesson,
                front_text=f'Color {i+1}',
                back_text=f'Spanish {i+1}',
                order=i
            )

        # Create quest
        self.quest = DailyQuest.objects.create(
            date=date.today(),
            title='Daily Colors Challenge',
            description='Test your Colors knowledge!',
            based_on_lesson=self.lesson,
            quest_type='flashcard',
            xp_reward=75
        )
        # Add questions
        for i in range(5):
            DailyQuestQuestion.objects.create(
                daily_quest=self.quest,
                question_text=f'Question {i+1}',
                answer_text=f'Answer {i+1}',
                order=i+1
            )

    def test_daily_quest_view_requires_authentication(self):
        """Test view redirects to login if not authenticated"""
        response = self.client.get(reverse('daily_quest'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_daily_quest_view_shows_quest_info_if_not_completed(self):
        """Test view shows quest info when not completed"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(reverse('daily_quest'))

        self.assertEqual(response.status_code, 200)
        # Check for the new quest page elements
        self.assertContains(response, 'Daily Quests')
        self.assertContains(response, 'Study for 15 Minutes')
        self.assertContains(response, 'Complete')
        self.assertContains(response, 'XP')

    def test_daily_quest_view_shows_completion_status_if_completed(self):
        """Test view shows completion status when quest completed"""
        self.client.login(username='testuser', password='testpass123')
        
        # Get the actual quests that would be generated for today
        from datetime import date
        from home.services.daily_quest_service import DailyQuestService
        
        today = date.today()
        quests = DailyQuestService.generate_quests_for_date(today)
        
        # Create completed attempt for time quest
        UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=quests['time_quest'],
            correct_answers=1,
            total_questions=1,
            xp_earned=50,
            is_completed=True
        )

        response = self.client.get(reverse('daily_quest'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quest Completed!')
        self.assertContains(response, 'XP earned')

    def test_daily_quest_view_generates_quest_if_not_exists(self):
        """Test view generates quests if none exist for today"""
        # Delete all quests
        DailyQuest.objects.all().delete()

        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(reverse('daily_quest'))

        self.assertEqual(response.status_code, 200)
        # Should have generated two new quests (time and lesson)
        self.assertEqual(DailyQuest.objects.filter(date=date.today()).count(), 2)


class TestQuestHistoryView(TestCase):
    """Test quest_history view"""

    def setUp(self):
        """Create test user with quest history"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create lesson
        self.lesson = Lesson.objects.create(
            title='Colors',
            slug='colors',
            lesson_type='flashcard',
            xp_value=100,
            is_published=True
        )

        # Create quests from past 3 days
        self.quests = []
        for i in range(3):
            quest_date = date.today() - timedelta(days=i)
            quest = DailyQuest.objects.create(
                date=quest_date,
                title=f'Quest {i}',
                description='Test',
                based_on_lesson=self.lesson,
                quest_type='flashcard',
                xp_reward=75
            )
            self.quests.append(quest)

            # Create completed attempt
            UserDailyQuestAttempt.objects.create(
                user=self.user,
                daily_quest=quest,
                correct_answers=4,
                total_questions=5,
                xp_earned=60,
                is_completed=True
            )

    def test_quest_history_requires_authentication(self):
        """Test view requires authentication"""
        response = self.client.get(reverse('quest_history'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_quest_history_shows_all_completed_quests(self):
        """Test view shows all completed quests"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(reverse('quest_history'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quest 0')
        self.assertContains(response, 'Quest 1')
        self.assertContains(response, 'Quest 2')
        self.assertContains(response, '4/5')

    def test_quest_history_shows_total_xp_earned(self):
        """Test view shows total XP earned from quests"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(reverse('quest_history'))

        self.assertEqual(response.status_code, 200)
        # 3 quests × 60 XP = 180 XP
        self.assertContains(response, '180')

    def test_quest_history_shows_empty_message_if_no_history(self):
        """Test view shows message if no completed quests"""
        # Create new user with no history
        User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='testpass123'
        )
        self.client.login(username='newuser', password='testpass123')

        response = self.client.get(reverse('quest_history'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No Quests Completed Yet')
