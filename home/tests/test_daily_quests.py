"""
Unit tests for Daily Quest models and functionality.
Following TDD - write tests first, then implement models.
"""
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from home.models import Lesson, DailyQuest, DailyQuestQuestion, UserDailyQuestAttempt


class TestDailyQuestModel(TestCase):
    """Test DailyQuest model functionality"""

    def setUp(self):
        """Create test lesson for daily quests"""
        self.lesson = Lesson.objects.create(
            title='Colors',
            slug='colors',
            lesson_type='flashcard',
            xp_value=100,
            is_published=True
        )

    def test_daily_quest_creation(self):
        """Test DailyQuest is created with correct fields"""
        quest = DailyQuest.objects.create(
            date=date.today(),
            title='Daily Colors Challenge',
            description='Test your Colors knowledge!',
            based_on_lesson=self.lesson,
            quest_type='flashcard',
            xp_reward=75  # 75% of 100
        )

        self.assertEqual(quest.date, date.today())
        self.assertEqual(quest.title, 'Daily Colors Challenge')
        self.assertEqual(quest.based_on_lesson, self.lesson)
        self.assertEqual(quest.quest_type, 'flashcard')
        self.assertEqual(quest.xp_reward, 75)

    def test_daily_quest_unique_date_constraint(self):
        """Test only one quest can exist per date"""
        DailyQuest.objects.create(
            date=date.today(),
            title='Quest 1',
            description='First quest',
            based_on_lesson=self.lesson,
            quest_type='flashcard',
            xp_reward=75
        )

        # Attempting to create another quest for same date should fail
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            DailyQuest.objects.create(
                date=date.today(),
                title='Quest 2',
                description='Second quest',
                based_on_lesson=self.lesson,
                quest_type='flashcard',
                xp_reward=75
            )

    def test_daily_quest_string_representation(self):
        """Test __str__ method returns correct format"""
        quest = DailyQuest.objects.create(
            date=date(2025, 11, 13),
            title='Daily Colors Challenge',
            description='Test quest',
            based_on_lesson=self.lesson,
            quest_type='flashcard',
            xp_reward=75
        )

        expected = "Daily Quest - 2025-11-13 - Spanish - Daily Colors Challenge"
        self.assertEqual(str(quest), expected)

    def test_daily_quest_ordering(self):
        """Test quests are ordered by date descending (newest first)"""
        quest1 = DailyQuest.objects.create(
            date=date(2025, 11, 11),
            title='Quest 1',
            description='Old quest',
            based_on_lesson=self.lesson,
            quest_type='flashcard',
            xp_reward=75
        )
        quest2 = DailyQuest.objects.create(
            date=date(2025, 11, 13),
            title='Quest 2',
            description='New quest',
            based_on_lesson=self.lesson,
            quest_type='flashcard',
            xp_reward=75
        )

        quests = DailyQuest.objects.all()
        self.assertEqual(quests[0], quest2)  # Newest first
        self.assertEqual(quests[1], quest1)


class TestDailyQuestQuestionModel(TestCase):
    """Test DailyQuestQuestion model functionality"""

    def setUp(self):
        """Create test quest for questions"""
        self.lesson = Lesson.objects.create(
            title='Colors',
            slug='colors',
            lesson_type='flashcard',
            xp_value=100,
            is_published=True
        )
        self.quest = DailyQuest.objects.create(
            date=date.today(),
            title='Daily Colors Challenge',
            description='Test quest',
            based_on_lesson=self.lesson,
            quest_type='flashcard',
            xp_reward=75
        )

    def test_flashcard_question_creation(self):
        """Test flashcard-type question is created correctly"""
        question = DailyQuestQuestion.objects.create(
            daily_quest=self.quest,
            question_text='What color is this?',
            answer_text='Red',
            order=1
        )

        self.assertEqual(question.daily_quest, self.quest)
        self.assertEqual(question.question_text, 'What color is this?')
        self.assertEqual(question.answer_text, 'Red')
        self.assertEqual(question.order, 1)

    def test_quiz_question_creation(self):
        """Test quiz-type question is created with options"""
        question = DailyQuestQuestion.objects.create(
            daily_quest=self.quest,
            question_text='What is red in Spanish?',
            options=['rojo', 'azul', 'verde', 'amarillo'],
            correct_index=0,
            order=1
        )

        self.assertEqual(question.question_text, 'What is red in Spanish?')
        self.assertEqual(len(question.options), 4)
        self.assertEqual(question.correct_index, 0)
        self.assertEqual(question.options[0], 'rojo')

    def test_question_ordering(self):
        """Test questions are ordered by order field"""
        q3 = DailyQuestQuestion.objects.create(
            daily_quest=self.quest,
            question_text='Q3',
            answer_text='A3',
            order=3
        )
        q1 = DailyQuestQuestion.objects.create(
            daily_quest=self.quest,
            question_text='Q1',
            answer_text='A1',
            order=1
        )
        q2 = DailyQuestQuestion.objects.create(
            daily_quest=self.quest,
            question_text='Q2',
            answer_text='A2',
            order=2
        )

        questions = self.quest.questions.all()
        self.assertEqual(questions[0], q1)
        self.assertEqual(questions[1], q2)
        self.assertEqual(questions[2], q3)

    def test_question_order_constraint(self):
        """Test question order must be between 1-5"""
        from django.db import IntegrityError, transaction

        # Order 1-5 should work
        DailyQuestQuestion.objects.create(
            daily_quest=self.quest,
            question_text='Q1',
            answer_text='A1',
            order=1
        )

        # Order 0 should fail
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                DailyQuestQuestion.objects.create(
                    daily_quest=self.quest,
                    question_text='Q0',
                    answer_text='A0',
                    order=0
                )

        # Order 6 should fail
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                DailyQuestQuestion.objects.create(
                    daily_quest=self.quest,
                    question_text='Q6',
                    answer_text='A6',
                    order=6
                )

    def test_question_unique_order_per_quest(self):
        """Test each quest can only have one question per order number"""
        DailyQuestQuestion.objects.create(
            daily_quest=self.quest,
            question_text='Q1',
            answer_text='A1',
            order=1
        )

        # Duplicate order in same quest should fail
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            DailyQuestQuestion.objects.create(
                daily_quest=self.quest,
                question_text='Q1 duplicate',
                answer_text='A1 duplicate',
                order=1
            )

    def test_question_string_representation(self):
        """Test __str__ method shows order and question text"""
        question = DailyQuestQuestion.objects.create(
            daily_quest=self.quest,
            question_text='What is the color of the sky?',
            answer_text='Blue',
            order=1
        )

        expected = "Q1: What is the color of the sky?"
        self.assertEqual(str(question), expected)


class TestUserDailyQuestAttemptModel(TestCase):
    """Test UserDailyQuestAttempt model functionality"""

    def setUp(self):
        """Create test user and quest"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.lesson = Lesson.objects.create(
            title='Colors',
            slug='colors',
            lesson_type='flashcard',
            xp_value=100,
            is_published=True
        )
        self.quest = DailyQuest.objects.create(
            date=date.today(),
            title='Daily Colors Challenge',
            description='Test quest',
            based_on_lesson=self.lesson,
            quest_type='flashcard',
            xp_reward=75
        )

    def test_attempt_creation(self):
        """Test UserDailyQuestAttempt is created correctly"""
        attempt = UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=self.quest
        )

        self.assertEqual(attempt.user, self.user)
        self.assertEqual(attempt.daily_quest, self.quest)
        self.assertEqual(attempt.total_questions, 5)
        self.assertEqual(attempt.correct_answers, 0)
        self.assertEqual(attempt.xp_earned, 0)
        self.assertFalse(attempt.is_completed)
        self.assertIsNotNone(attempt.started_at)
        self.assertIsNone(attempt.completed_at)

    def test_attempt_unique_per_user_per_quest(self):
        """Test user can only attempt each quest once"""
        UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=self.quest
        )

        # Second attempt should fail
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            UserDailyQuestAttempt.objects.create(
                user=self.user,
                daily_quest=self.quest
            )

    def test_attempt_score_property(self):
        """Test score property returns X/5 format"""
        attempt = UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=self.quest,
            correct_answers=3,
            total_questions=5
        )

        self.assertEqual(attempt.score, "3/5")

    def test_attempt_score_percentage_property(self):
        """Test score_percentage property calculates correctly"""
        attempt = UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=self.quest,
            correct_answers=4,
            total_questions=5
        )

        self.assertEqual(attempt.score_percentage, 80.0)

    def test_attempt_score_percentage_zero_total(self):
        """Test score_percentage handles zero total_questions"""
        attempt = UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=self.quest,
            total_questions=0
        )

        self.assertEqual(attempt.score_percentage, 0)

    def test_calculate_xp_method(self):
        """Test calculate_xp returns correct XP based on score"""
        attempt = UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=self.quest,
            correct_answers=4,
            total_questions=5
        )

        # 75 XP * (4/5) = 60 XP
        calculated_xp = attempt.calculate_xp()
        self.assertEqual(calculated_xp, 60)

    def test_calculate_xp_perfect_score(self):
        """Test calculate_xp with perfect score"""
        attempt = UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=self.quest,
            correct_answers=5,
            total_questions=5
        )

        # 75 XP * (5/5) = 75 XP
        calculated_xp = attempt.calculate_xp()
        self.assertEqual(calculated_xp, 75)

    def test_calculate_xp_zero_correct(self):
        """Test calculate_xp with zero correct answers"""
        attempt = UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=self.quest,
            correct_answers=0,
            total_questions=5
        )

        # 75 XP * (0/5) = 0 XP
        calculated_xp = attempt.calculate_xp()
        self.assertEqual(calculated_xp, 0)

    def test_attempt_string_representation(self):
        """Test __str__ method shows username, date, and score"""
        attempt = UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=self.quest,
            correct_answers=3,
            total_questions=5
        )

        expected = f"testuser - {date.today()} - 3/5"
        self.assertEqual(str(attempt), expected)

    def test_attempt_ordering(self):
        """Test attempts are ordered by started_at descending"""
        # Create quest for yesterday
        yesterday_quest = DailyQuest.objects.create(
            date=date.today() - timedelta(days=1),
            title='Yesterday Quest',
            description='Old quest',
            based_on_lesson=self.lesson,
            quest_type='flashcard',
            xp_reward=75
        )

        # Create attempts (older first)
        old_attempt = UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=yesterday_quest
        )
        new_attempt = UserDailyQuestAttempt.objects.create(
            user=self.user,
            daily_quest=self.quest
        )

        attempts = UserDailyQuestAttempt.objects.all()
        self.assertEqual(attempts[0], new_attempt)  # Newest first
        self.assertEqual(attempts[1], old_attempt)
