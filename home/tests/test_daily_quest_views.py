"""
Unit tests for Daily Quest views (NEW single-quest system).
Tests the views for the redesigned ONE quest with 5 questions.
"""
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from home.models import (
    DailyQuest,
    DailyQuestQuestion,
    Lesson,
    LessonQuizQuestion,
    UserDailyQuestAttempt,
)


class TestDailyQuestView(TestCase):
    """Test daily_quest_view for new single-quest system"""

    def setUp(self):
        """Create test user and lessons"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create lesson with quiz questions
        self.lesson = Lesson.objects.create(
            title='Spanish Colors',
            slug='colors',
            language='Spanish',
            xp_value=100,
            is_published=True
        )
        for i in range(10):
            LessonQuizQuestion.objects.create(
                lesson=self.lesson,
                question=f'What color is this? {i+1}',
                options=['Red', 'Blue', 'Green', 'Yellow'],
                correct_index=0,
                order=i
            )

    def test_daily_quest_view_requires_authentication(self):
        """Test view redirects to login if not authenticated"""
        response = self.client.get(reverse('daily_quest'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_daily_quest_view_shows_quest_with_5_questions(self):
        """Test view shows quest with exactly 5 questions when not completed"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(reverse('daily_quest'))

        self.assertEqual(response.status_code, 200)
        # Check for new single-quest UI elements
        self.assertContains(response, 'Daily Challenge')
        self.assertContains(response, 'Answer 5 random questions')
        self.assertContains(response, 'Reward: 50 XP')

        # Should have 5 questions displayed
        quest = response.context['quest']
        questions = response.context['questions']
        self.assertEqual(len(questions), 5)

    def test_daily_quest_view_shows_completion_status(self):
        """Test view shows completion status when quest completed"""
        self.client.login(username='testuser', password='testpass123')

        # Generate quest
        from home.services.daily_quest_service import DailyQuestService
        quest = DailyQuestService.generate_quest_for_user(self.user, date.today())

        # Create completed attempt
        UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=quest,
            correct_answers=4,
            total_questions=5,
            xp_earned=40,
            is_completed=True
        )

        response = self.client.get(reverse('daily_quest'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Challenge Completed!')
        self.assertContains(response, '4/5')  # Score
        self.assertContains(response, '+40')  # XP earned

    def test_daily_quest_view_generates_quest_if_not_exists(self):
        """Test view generates quest if none exist for today"""
        # Ensure no quests exist
        DailyQuest.objects.all().delete()

        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(reverse('daily_quest'))

        self.assertEqual(response.status_code, 200)
        # Should have generated ONE new quest
        self.assertEqual(DailyQuest.objects.filter(date=date.today()).count(), 1)
        # With 5 questions
        quest = DailyQuest.objects.get(date=date.today())
        self.assertEqual(DailyQuestQuestion.objects.filter(daily_quest=quest).count(), 5)


class TestDailyQuestSubmitView(TestCase):
    """Test daily_quest_submit view"""

    def setUp(self):
        """Create test user and quest"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create lesson with quiz questions
        self.lesson = Lesson.objects.create(
            title='Spanish Numbers',
            slug='numbers',
            language='Spanish',
            xp_value=100,
            is_published=True
        )
        for i in range(10):
            LessonQuizQuestion.objects.create(
                lesson=self.lesson,
                question=f'What number is {i+1}?',
                options=['Uno', 'Dos', 'Tres', 'Cuatro'],
                correct_index=0,
                order=i
            )

        # Generate quest
        from home.services.daily_quest_service import DailyQuestService
        self.quest = DailyQuestService.generate_quest_for_user(self.user, date.today())
        self.questions = list(DailyQuestQuestion.objects.filter(daily_quest=self.quest))

    def test_submit_requires_authentication(self):
        """Test submit endpoint requires authentication"""
        response = self.client.post(reverse('daily_quest_submit'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_submit_requires_post(self):
        """Test submit endpoint requires POST method"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(reverse('daily_quest_submit'))

        self.assertEqual(response.status_code, 302)

    def test_submit_creates_attempt_with_correct_score(self):
        """Test submitting answers creates attempt with correct score"""
        self.client.login(username='testuser', password='testpass123')

        # Submit all correct answers (as indices)
        post_data = {
            f'question_{q.id}': str(q.correct_index)
            for q in self.questions
        }

        response = self.client.post(reverse('daily_quest_submit'), post_data)

        # Should redirect back to quest page
        self.assertEqual(response.status_code, 302)

        # Should create attempt
        attempt = UserDailyQuestAttempt.objects.get(user=self.user, daily_quest=self.quest)
        self.assertEqual(attempt.correct_answers, 5)
        self.assertEqual(attempt.total_questions, 5)
        self.assertEqual(attempt.xp_earned, 50)
        self.assertTrue(attempt.is_completed)

    def test_submit_prevents_duplicate_completion(self):
        """Test cannot submit same quest twice"""
        self.client.login(username='testuser', password='testpass123')

        # Submit first time
        post_data = {
            f'question_{q.id}': str(q.correct_index)
            for q in self.questions
        }
        self.client.post(reverse('daily_quest_submit'), post_data)

        # Try to submit again
        response = self.client.post(reverse('daily_quest_submit'), post_data)

        # Should still have only one attempt
        self.assertEqual(UserDailyQuestAttempt.objects.filter(
            user=self.user,
            daily_quest=self.quest,
            is_completed=True
        ).count(), 1)


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
            language='Spanish',
            xp_value=100,
            is_published=True
        )

        # Create quests from past 3 days
        self.quests = []
        for i in range(3):
            quest_date = date.today() - timedelta(days=i)
            quest = DailyQuest.objects.create(
                date=quest_date,
                title='Daily Challenge',
                description='Answer 5 questions',
                based_on_lesson=self.lesson,
                quest_type='quiz',
                xp_reward=50
            )
            self.quests.append(quest)

            # Create completed attempt
            UserDailyQuestAttempt.objects.create(
                user=self.user,
                daily_quest=quest,
                correct_answers=4,
                total_questions=5,
                xp_earned=40,
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
        self.assertContains(response, 'Daily Challenge')
        self.assertContains(response, '4/5')
        # 3 quests should be visible
        attempts = response.context['attempts']
        self.assertEqual(attempts.count(), 3)

    def test_quest_history_shows_total_xp_earned(self):
        """Test view shows total XP earned from quests"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(reverse('quest_history'))

        self.assertEqual(response.status_code, 200)
        # 3 quests × 40 XP = 120 XP
        total_xp = response.context['total_quest_xp']
        self.assertEqual(total_xp, 120)

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
        # Check for empty state message
        attempts = response.context['attempts']
        self.assertEqual(attempts.count(), 0)
