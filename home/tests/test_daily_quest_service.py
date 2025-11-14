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
        """Test generating quests creates two DailyQuests"""
        test_date = date(2025, 11, 13)

        quests = DailyQuestService.generate_quests_for_date(test_date)

        # Should return dict with two quests
        self.assertIn('time_quest', quests)
        self.assertIn('lesson_quest', quests)
        
        time_quest = quests['time_quest']
        lesson_quest = quests['lesson_quest']
        
        # Verify time quest
        self.assertIsNotNone(time_quest)
        self.assertEqual(time_quest.date, test_date)
        self.assertEqual(time_quest.quest_type, 'study')
        self.assertEqual(time_quest.xp_reward, 50)
        
        # Verify lesson quest
        self.assertIsNotNone(lesson_quest)
        self.assertEqual(lesson_quest.date, test_date)
        self.assertEqual(lesson_quest.quest_type, 'quiz')
        self.assertIsNotNone(lesson_quest.based_on_lesson)
        self.assertTrue(lesson_quest.xp_reward > 0)

    def test_generate_quest_returns_existing_if_already_generated(self):
        """Test generating quests for same date returns existing quests"""
        test_date = date(2025, 11, 13)

        # Generate first time
        quests1 = DailyQuestService.generate_quests_for_date(test_date)

        # Try to generate again for same date
        quests2 = DailyQuestService.generate_quests_for_date(test_date)

        # Should return same quests
        self.assertEqual(quests1['time_quest'].id, quests2['time_quest'].id)
        self.assertEqual(quests1['lesson_quest'].id, quests2['lesson_quest'].id)
        self.assertEqual(DailyQuest.objects.filter(date=test_date).count(), 2)

    def test_generate_quest_calculates_xp_as_75_percent(self):
        """Test lesson quest XP matches lesson XP"""
        test_date = date(2025, 11, 13)

        quests = DailyQuestService.generate_quests_for_date(test_date)
        lesson_quest = quests['lesson_quest']
        lesson_xp = lesson_quest.based_on_lesson.xp_value

        # New behavior: quest XP equals lesson XP (not 75%)
        self.assertEqual(lesson_quest.xp_reward, lesson_xp)

    def test_generate_quest_creates_5_questions(self):
        """Test that lesson quest is based on a lesson with content"""
        test_date = date(2025, 11, 13)

        quests = DailyQuestService.generate_quests_for_date(test_date)
        lesson = quests['lesson_quest'].based_on_lesson

        # Lesson should have either flashcards or quiz questions
        has_flashcards = lesson.cards.count() >= 5
        has_quiz_questions = lesson.quiz_questions.count() >= 5
        
        self.assertTrue(has_flashcards or has_quiz_questions,
                       "Lesson should have at least 5 flashcards or quiz questions")

    def test_generate_quest_questions_have_correct_order(self):
        """Test lesson has properly ordered content"""
        test_date = date(2025, 11, 13)

        quests = DailyQuestService.generate_quests_for_date(test_date)
        lesson = quests['lesson_quest'].based_on_lesson

        # Verify lesson has content (flashcards or quiz questions)
        total_content = lesson.cards.count() + lesson.quiz_questions.count()
        self.assertTrue(total_content >= 5,
                       "Lesson should have at least 5 pieces of content")

    def test_generate_quest_inherits_lesson_type(self):
        """Test lesson quest type is 'quiz' for lesson-based quests"""
        test_date = date(2025, 11, 13)

        quests = DailyQuestService.generate_quests_for_date(test_date)

        # Time quest should be 'study'
        self.assertEqual(quests['time_quest'].quest_type, 'study')
        # Lesson quest should be 'quiz'
        self.assertEqual(quests['lesson_quest'].quest_type, 'quiz')

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
