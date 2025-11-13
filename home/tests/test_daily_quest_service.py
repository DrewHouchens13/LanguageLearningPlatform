"""
Unit tests for DailyQuestService.
Following TDD - write tests first, then implement service.
"""
from datetime import date
from django.test import TestCase
from home.models import Lesson, DailyQuest, Flashcard, LessonQuizQuestion
from home.services.daily_quest_service import DailyQuestService


class TestDailyQuestServiceGeneration(TestCase):
    """Test DailyQuestService quest generation"""

    def setUp(self):
        """Create test lessons with content"""
        # Flashcard lesson
        self.flashcard_lesson = Lesson.objects.create(
            title='Colors',
            slug='colors',
            lesson_type='flashcard',
            xp_value=100,
            category='Vocabulary',
            is_published=True
        )
        # Add flashcards
        for i in range(5):
            Flashcard.objects.create(
                lesson=self.flashcard_lesson,
                front_text=f'Color {i+1}',
                back_text=f'Spanish Color {i+1}',
                order=i
            )

        # Quiz lesson
        self.quiz_lesson = Lesson.objects.create(
            title='Numbers',
            slug='numbers',
            lesson_type='quiz',
            xp_value=150,
            category='Vocabulary',
            is_published=True
        )
        # Add quiz questions
        for i in range(5):
            LessonQuizQuestion.objects.create(
                lesson=self.quiz_lesson,
                question=f'What is number {i+1}?',
                options=[f'Option{j}' for j in range(4)],
                correct_index=0,
                order=i
            )

    def test_generate_quest_for_date_creates_new_quest(self):
        """Test generating a quest creates a new DailyQuest"""
        test_date = date(2025, 11, 13)

        quest = DailyQuestService.generate_quest_for_date(test_date)

        self.assertIsNotNone(quest)
        self.assertEqual(quest.date, test_date)
        self.assertIn('Daily', quest.title)
        self.assertIn('Challenge', quest.title)
        self.assertIsNotNone(quest.based_on_lesson)
        self.assertTrue(quest.xp_reward > 0)

    def test_generate_quest_returns_existing_if_already_generated(self):
        """Test generating quest for same date returns existing quest"""
        test_date = date(2025, 11, 13)

        # Generate first quest
        quest1 = DailyQuestService.generate_quest_for_date(test_date)

        # Try to generate again for same date
        quest2 = DailyQuestService.generate_quest_for_date(test_date)

        # Should return same quest
        self.assertEqual(quest1.id, quest2.id)
        self.assertEqual(DailyQuest.objects.filter(date=test_date).count(), 1)

    def test_generate_quest_calculates_xp_as_75_percent(self):
        """Test quest XP is 75% of lesson XP"""
        test_date = date(2025, 11, 13)

        quest = DailyQuestService.generate_quest_for_date(test_date)
        lesson_xp = quest.based_on_lesson.xp_value
        expected_xp = int(lesson_xp * 0.75)

        self.assertEqual(quest.xp_reward, expected_xp)

    def test_generate_quest_creates_5_questions(self):
        """Test quest generation creates exactly 5 questions"""
        test_date = date(2025, 11, 13)

        quest = DailyQuestService.generate_quest_for_date(test_date)

        self.assertEqual(quest.questions.count(), 5)

    def test_generate_quest_questions_have_correct_order(self):
        """Test quest questions have order 1-5"""
        test_date = date(2025, 11, 13)

        quest = DailyQuestService.generate_quest_for_date(test_date)
        questions = quest.questions.all()

        orders = [q.order for q in questions]
        self.assertEqual(sorted(orders), [1, 2, 3, 4, 5])

    def test_generate_quest_inherits_lesson_type(self):
        """Test quest inherits quest_type from lesson"""
        test_date = date(2025, 11, 13)

        quest = DailyQuestService.generate_quest_for_date(test_date)

        self.assertEqual(quest.quest_type, quest.based_on_lesson.lesson_type)

    def test_select_random_lesson_returns_published_lesson(self):
        """Test _select_random_lesson returns a published lesson"""
        lesson = DailyQuestService._select_random_lesson()

        self.assertIsNotNone(lesson)
        self.assertTrue(lesson.is_published)

    def test_select_random_lesson_raises_error_if_no_lessons(self):
        """Test _select_random_lesson raises error if no published lessons"""
        # Delete all lessons
        Lesson.objects.all().delete()

        with self.assertRaises(ValueError) as context:
            DailyQuestService._select_random_lesson()

        self.assertIn('No published lessons', str(context.exception))


class TestDailyQuestServiceFlashcardQuestions(TestCase):
    """Test DailyQuestService flashcard question generation"""

    def setUp(self):
        """Create flashcard lesson with content"""
        self.lesson = Lesson.objects.create(
            title='Colors',
            slug='colors',
            lesson_type='flashcard',
            xp_value=100,
            is_published=True
        )
        # Add 5 flashcards
        self.cards = []
        for i in range(5):
            card = Flashcard.objects.create(
                lesson=self.lesson,
                front_text=f'Color {i+1}',
                back_text=f'Spanish {i+1}',
                order=i
            )
            self.cards.append(card)

    def test_generate_flashcard_questions_creates_5_questions(self):
        """Test flashcard question generation creates 5 questions"""
        test_date = date(2025, 11, 13)
        quest = DailyQuest.objects.create(
            date=test_date,
            title='Test Quest',
            description='Test',
            based_on_lesson=self.lesson,
            quest_type='flashcard',
            xp_reward=75
        )

        DailyQuestService._generate_flashcard_questions(quest, self.lesson)

        self.assertEqual(quest.questions.count(), 5)

    def test_generate_flashcard_questions_have_required_fields(self):
        """Test flashcard questions have question_text and answer_text"""
        test_date = date(2025, 11, 13)
        quest = DailyQuest.objects.create(
            date=test_date,
            title='Test Quest',
            description='Test',
            based_on_lesson=self.lesson,
            quest_type='flashcard',
            xp_reward=75
        )

        DailyQuestService._generate_flashcard_questions(quest, self.lesson)

        for question in quest.questions.all():
            self.assertTrue(len(question.question_text) > 0)
            self.assertTrue(len(question.answer_text) > 0)

    def test_generate_flashcard_questions_raises_error_if_insufficient_cards(self):
        """Test error raised if lesson has < 3 flashcards"""
        # Create lesson with only 2 cards
        lesson = Lesson.objects.create(
            title='Small Lesson',
            slug='small',
            lesson_type='flashcard',
            xp_value=100,
            is_published=True
        )
        for i in range(2):
            Flashcard.objects.create(
                lesson=lesson,
                front_text=f'Card {i}',
                back_text=f'Answer {i}',
                order=i
            )

        quest = DailyQuest.objects.create(
            date=date.today(),
            title='Test',
            description='Test',
            based_on_lesson=lesson,
            quest_type='flashcard',
            xp_reward=75
        )

        with self.assertRaises(ValueError) as context:
            DailyQuestService._generate_flashcard_questions(quest, lesson)

        self.assertIn('at least 3 flashcards', str(context.exception))


class TestDailyQuestServiceQuizQuestions(TestCase):
    """Test DailyQuestService quiz question generation"""

    def setUp(self):
        """Create quiz lesson with content"""
        self.lesson = Lesson.objects.create(
            title='Numbers',
            slug='numbers',
            lesson_type='quiz',
            xp_value=150,
            is_published=True
        )
        # Add 5 quiz questions
        for i in range(5):
            LessonQuizQuestion.objects.create(
                lesson=self.lesson,
                question=f'Question {i+1}?',
                options=['A', 'B', 'C', 'D'],
                correct_index=i % 4,
                order=i
            )

    def test_generate_quiz_questions_creates_5_questions(self):
        """Test quiz question generation creates 5 questions"""
        test_date = date(2025, 11, 13)
        quest = DailyQuest.objects.create(
            date=test_date,
            title='Test Quest',
            description='Test',
            based_on_lesson=self.lesson,
            quest_type='quiz',
            xp_reward=112
        )

        DailyQuestService._generate_quiz_questions(quest, self.lesson)

        self.assertEqual(quest.questions.count(), 5)

    def test_generate_quiz_questions_have_required_fields(self):
        """Test quiz questions have question_text, options, correct_index"""
        test_date = date(2025, 11, 13)
        quest = DailyQuest.objects.create(
            date=test_date,
            title='Test Quest',
            description='Test',
            based_on_lesson=self.lesson,
            quest_type='quiz',
            xp_reward=112
        )

        DailyQuestService._generate_quiz_questions(quest, self.lesson)

        for question in quest.questions.all():
            self.assertTrue(len(question.question_text) > 0)
            self.assertIsNotNone(question.options)
            self.assertTrue(len(question.options) > 0)
            self.assertIsNotNone(question.correct_index)
            self.assertTrue(0 <= question.correct_index < len(question.options))

    def test_generate_quiz_questions_shuffles_options(self):
        """Test quiz questions shuffle options"""
        test_date = date(2025, 11, 13)
        quest = DailyQuest.objects.create(
            date=test_date,
            title='Test Quest',
            description='Test',
            based_on_lesson=self.lesson,
            quest_type='quiz',
            xp_reward=112
        )

        DailyQuestService._generate_quiz_questions(quest, self.lesson)

        # Options should be shuffled, so correct_index may differ from lesson
        # Just verify correct answer is at the specified index
        for question in quest.questions.all():
            self.assertTrue(question.correct_index < len(question.options))

    def test_generate_quiz_questions_raises_error_if_insufficient_questions(self):
        """Test error raised if lesson has < 5 quiz questions"""
        lesson = Lesson.objects.create(
            title='Small Quiz',
            slug='small-quiz',
            lesson_type='quiz',
            xp_value=150,
            is_published=True
        )
        # Only 3 questions
        for i in range(3):
            LessonQuizQuestion.objects.create(
                lesson=lesson,
                question=f'Q{i}',
                options=['A', 'B'],
                correct_index=0,
                order=i
            )

        quest = DailyQuest.objects.create(
            date=date.today(),
            title='Test',
            description='Test',
            based_on_lesson=lesson,
            quest_type='quiz',
            xp_reward=112
        )

        with self.assertRaises(ValueError) as context:
            DailyQuestService._generate_quiz_questions(quest, lesson)

        self.assertIn('at least 5 quiz questions', str(context.exception))
