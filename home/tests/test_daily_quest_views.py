"""
Unit tests for Daily Quest views.
Following TDD - write tests first, then implement views.
"""
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from home.models import Lesson, DailyQuest, DailyQuestQuestion, UserDailyQuestAttempt, Flashcard


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
        self.assertContains(response, 'Daily Colors Challenge')
        self.assertContains(response, '75 XP')
        self.assertContains(response, 'Start Quest')

    def test_daily_quest_view_shows_completion_status_if_completed(self):
        """Test view shows completion status when quest completed"""
        self.client.login(username='testuser', password='testpass123')

        # Create completed attempt
        UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=self.quest,
            correct_answers=4,
            total_questions=5,
            xp_earned=60,
            is_completed=True
        )

        response = self.client.get(reverse('daily_quest'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Quest Completed')
        self.assertContains(response, '4/5')
        self.assertContains(response, 'XP Earned: 60')
        self.assertNotContains(response, 'Start Quest')

    def test_daily_quest_view_generates_quest_if_not_exists(self):
        """Test view generates quest if none exists for today"""
        # Delete existing quest
        self.quest.delete()

        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(reverse('daily_quest'))

        self.assertEqual(response.status_code, 200)
        # Should have generated a new quest
        self.assertTrue(DailyQuest.objects.filter(date=date.today()).exists())


class TestStartDailyQuestView(TestCase):
    """Test start_daily_quest view"""

    def setUp(self):
        """Create test user and quest"""
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

        # Create quest
        self.quest = DailyQuest.objects.create(
            date=date.today(),
            title='Daily Colors Challenge',
            description='Test quest',
            based_on_lesson=self.lesson,
            quest_type='flashcard',
            xp_reward=75
        )
        # Add questions
        for i in range(5):
            DailyQuestQuestion.objects.create(
                daily_quest=self.quest,
                question_text=f'Q{i+1}',
                answer_text=f'A{i+1}',
                order=i+1
            )

    def test_start_quest_requires_authentication(self):
        """Test view requires authentication"""
        response = self.client.post(reverse('start_daily_quest'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_start_quest_requires_post(self):
        """Test view requires POST method"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(reverse('start_daily_quest'))

        self.assertEqual(response.status_code, 405)  # Method not allowed

    def test_start_quest_creates_attempt(self):
        """Test view creates UserDailyQuestAttempt"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.post(reverse('start_daily_quest'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            UserDailyQuestAttempt.objects.filter(
                user=self.user,
                daily_quest=self.quest
            ).exists()
        )

    def test_start_quest_prevents_duplicate_attempts(self):
        """Test view prevents creating duplicate attempts"""
        self.client.login(username='testuser', password='testpass123')

        # Create first attempt
        self.client.post(reverse('start_daily_quest'))

        # Try to create duplicate
        response = self.client.post(reverse('start_daily_quest'))

        self.assertEqual(response.status_code, 400)
        # Should only have one attempt
        self.assertEqual(
            UserDailyQuestAttempt.objects.filter(
                user=self.user,
                daily_quest=self.quest
            ).count(),
            1
        )

    def test_start_quest_returns_json_with_questions(self):
        """Test view returns JSON with quest questions"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.post(reverse('start_daily_quest'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('questions', data)
        self.assertEqual(len(data['questions']), 5)


class TestSubmitDailyQuestView(TestCase):
    """Test submit_daily_quest view"""

    def setUp(self):
        """Create test user, quest, and attempt"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Create user profile for XP tracking
        from home.models import UserProfile
        if not hasattr(self.user, 'profile'):
            UserProfile.objects.create(user=self.user)

        # Create lesson
        self.lesson = Lesson.objects.create(
            title='Colors',
            slug='colors',
            lesson_type='flashcard',
            xp_value=100,
            is_published=True
        )

        # Create quest
        self.quest = DailyQuest.objects.create(
            date=date.today(),
            title='Daily Colors Challenge',
            description='Test quest',
            based_on_lesson=self.lesson,
            quest_type='flashcard',
            xp_reward=75
        )
        # Add questions
        self.questions = []
        for i in range(5):
            q = DailyQuestQuestion.objects.create(
                daily_quest=self.quest,
                question_text=f'Question {i+1}',
                answer_text=f'Answer {i+1}',
                order=i+1
            )
            self.questions.append(q)

        # Create attempt
        self.attempt = UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=self.quest
        )

    def test_submit_quest_requires_authentication(self):
        """Test view requires authentication"""
        response = self.client.post(reverse('submit_daily_quest'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_submit_quest_requires_post(self):
        """Test view requires POST method"""
        self.client.login(username='testuser', password='testpass123')

        response = self.client.get(reverse('submit_daily_quest'))

        self.assertEqual(response.status_code, 405)

    def test_submit_quest_calculates_score_correctly(self):
        """Test view calculates correct score"""
        self.client.login(username='testuser', password='testpass123')

        # Submit 4 correct answers
        answers = {
            str(self.questions[0].id): 'Answer 1',
            str(self.questions[1].id): 'Answer 2',
            str(self.questions[2].id): 'Answer 3',
            str(self.questions[3].id): 'Answer 4',
            str(self.questions[4].id): 'Wrong Answer'
        }

        response = self.client.post(
            reverse('submit_daily_quest'),
            data=answers
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['correct_answers'], 4)
        self.assertEqual(data['total_questions'], 5)

    def test_submit_quest_awards_xp_correctly(self):
        """Test view awards XP based on score"""
        self.client.login(username='testuser', password='testpass123')

        initial_xp = self.user.profile.total_xp

        # Submit 4/5 correct (should award 60 XP: 75 * 4/5)
        answers = {
            str(self.questions[0].id): 'Answer 1',
            str(self.questions[1].id): 'Answer 2',
            str(self.questions[2].id): 'Answer 3',
            str(self.questions[3].id): 'Answer 4',
            str(self.questions[4].id): 'Wrong'
        }

        response = self.client.post(reverse('submit_daily_quest'), data=answers)

        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.total_xp, initial_xp + 60)

    def test_submit_quest_marks_attempt_as_completed(self):
        """Test view marks attempt as completed"""
        self.client.login(username='testuser', password='testpass123')

        answers = {str(q.id): f'Answer {i+1}' for i, q in enumerate(self.questions)}

        response = self.client.post(reverse('submit_daily_quest'), data=answers)

        self.assertEqual(response.status_code, 200)
        self.attempt.refresh_from_db()
        self.assertTrue(self.attempt.is_completed)
        self.assertIsNotNone(self.attempt.completed_at)

    def test_submit_quest_prevents_resubmission(self):
        """Test view prevents submitting completed quest"""
        self.client.login(username='testuser', password='testpass123')

        # Mark as completed
        self.attempt.is_completed = True
        self.attempt.save()

        answers = {str(q.id): 'Answer' for q in self.questions}
        response = self.client.post(reverse('submit_daily_quest'), data=answers)

        self.assertEqual(response.status_code, 400)


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
        self.assertContains(response, 'No completed quests')
