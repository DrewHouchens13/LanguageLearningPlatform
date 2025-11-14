"""
Unit tests for DailyQuestService (NEW single-quest system).
Tests the redesigned service with ONE quest containing 5 random questions.
"""
from datetime import date
from django.contrib.auth.models import User
from django.test import TestCase
from home.models import (
    DailyQuest,
    DailyQuestQuestion,
    Lesson,
    LessonCompletion,
    LessonQuizQuestion,
    UserProfile,
)
from home.services.daily_quest_service import DailyQuestService


class TestDailyQuestServiceGeneration(TestCase):
    """Test DailyQuestService quest generation for new single-quest system"""

    def setUp(self):
        """Create test user and lessons with quiz questions"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)

        # Create Spanish lesson with quiz questions
        self.spanish_lesson = Lesson.objects.create(
            title='Spanish Colors',
            slug='spanish-colors',
            language='Spanish',
            xp_value=100,
            difficulty_level='beginner',
            is_published=True
        )
        for i in range(10):
            LessonQuizQuestion.objects.create(
                lesson=self.spanish_lesson,
                question=f'What color is this? {i+1}',
                options=['Red', 'Blue', 'Green', 'Yellow'],
                correct_index=0,
                order=i
            )

        # Create French lesson with quiz questions
        self.french_lesson = Lesson.objects.create(
            title='French Numbers',
            slug='french-numbers',
            language='French',
            xp_value=150,
            difficulty_level='beginner',
            is_published=True
        )
        for i in range(10):
            LessonQuizQuestion.objects.create(
                lesson=self.french_lesson,
                question=f'What number is this? {i+1}',
                options=['Un', 'Deux', 'Trois', 'Quatre'],
                correct_index=0,
                order=i
            )

    def test_generate_quest_creates_single_quest(self):
        """Test generating quest creates ONE DailyQuest"""
        test_date = date(2025, 11, 14)

        quest = DailyQuestService.generate_quest_for_user(self.user, test_date)

        # Should create one quest
        self.assertIsNotNone(quest)
        self.assertEqual(quest.date, test_date)
        self.assertEqual(quest.quest_type, 'quiz')
        self.assertEqual(quest.xp_reward, 50)
        self.assertEqual(quest.title, 'Daily Challenge')

    def test_generate_quest_creates_5_questions(self):
        """Test quest contains exactly 5 DailyQuestQuestion records"""
        test_date = date(2025, 11, 14)

        quest = DailyQuestService.generate_quest_for_user(self.user, test_date)
        questions = DailyQuestQuestion.objects.filter(daily_quest=quest)

        self.assertEqual(questions.count(), 5)

    def test_generate_quest_returns_existing_if_already_generated(self):
        """Test generating quest for same date returns existing quest"""
        test_date = date(2025, 11, 14)

        # Generate first time
        quest1 = DailyQuestService.generate_quest_for_user(self.user, test_date)

        # Try to generate again for same date
        quest2 = DailyQuestService.generate_quest_for_user(self.user, test_date)

        # Should return same quest
        self.assertEqual(quest1.id, quest2.id)
        self.assertEqual(DailyQuest.objects.filter(date=test_date).count(), 1)

    def test_questions_from_all_lessons_if_no_completions(self):
        """Test questions pulled from all published lessons if user hasn't completed any"""
        test_date = date(2025, 11, 14)

        quest = DailyQuestService.generate_quest_for_user(self.user, test_date)
        questions = DailyQuestQuestion.objects.filter(daily_quest=quest)

        # All 5 questions should exist
        self.assertEqual(questions.count(), 5)

        # Questions can be from any published lesson
        for question in questions:
            self.assertIn(question.lesson, [self.spanish_lesson, self.french_lesson])

    def test_questions_from_completed_lessons_only(self):
        """Test questions pulled only from completed lessons if user has completions"""
        # Mark Spanish lesson as completed
        LessonCompletion.objects.create(
            user=self.user,
            lesson=self.spanish_lesson,
            duration_minutes=5
        )

        test_date = date(2025, 11, 14)
        quest = DailyQuestService.generate_quest_for_user(self.user, test_date)
        questions = DailyQuestQuestion.objects.filter(daily_quest=quest)

        # All questions should be from Spanish lesson only
        for question in questions:
            self.assertEqual(question.lesson, self.spanish_lesson)

    def test_raises_error_if_insufficient_questions(self):
        """Test ValueError raised if fewer than 5 questions available"""
        # Create lesson with only 3 questions
        small_lesson = Lesson.objects.create(
            title='Small Lesson',
            slug='small',
            language='German',
            is_published=True
        )
        for i in range(3):
            LessonQuizQuestion.objects.create(
                lesson=small_lesson,
                question_text=f'Question {i+1}',
                correct_answer='Answer',
                option_a='Answer',
                option_b='Wrong',
                option_c='Wrong',
                option_d='Wrong'
            )

        # Mark as completed (so it's the only source)
        LessonCompletion.objects.create(
            user=self.user,
            lesson=small_lesson,
            duration_minutes=5
        )

        # Delete other lessons
        self.spanish_lesson.delete()
        self.french_lesson.delete()

        test_date = date(2025, 11, 14)

        with self.assertRaises(ValueError) as context:
            DailyQuestService.generate_quest_for_user(self.user, test_date)

        self.assertIn('Insufficient questions', str(context.exception))

    def test_calculate_quest_score_perfect_score(self):
        """Test score calculation with all correct answers"""
        test_date = date(2025, 11, 14)
        quest = DailyQuestService.generate_quest_for_user(self.user, test_date)
        questions = DailyQuestQuestion.objects.filter(daily_quest=quest)

        # Submit all correct answers (indices)
        answers = {str(q.id): str(q.correct_index) for q in questions}

        correct, total, xp = DailyQuestService.calculate_quest_score(quest, answers)

        self.assertEqual(correct, 5)
        self.assertEqual(total, 5)
        self.assertEqual(xp, 50)  # 100% of 50 XP reward

    def test_calculate_quest_score_partial_score(self):
        """Test score calculation with some correct answers"""
        test_date = date(2025, 11, 14)
        quest = DailyQuestService.generate_quest_for_user(self.user, test_date)
        questions = list(DailyQuestQuestion.objects.filter(quest=quest))

        # Submit 3 correct, 2 wrong
        answers = {
            str(questions[0].id): str(questions[0].correct_index),
            str(questions[1].id): str(questions[1].correct_index),
            str(questions[2].id): str(questions[2].correct_index),
            str(questions[3].id): '99',  # Wrong index
            str(questions[4].id): '99',  # Wrong index
        }

        correct, total, xp = DailyQuestService.calculate_quest_score(quest, answers)

        self.assertEqual(correct, 3)
        self.assertEqual(total, 5)
        self.assertEqual(xp, 30)  # 60% of 50 XP = 30

    def test_get_weekly_stats_no_attempts(self):
        """Test weekly stats returns zeros if no attempts"""
        stats = DailyQuestService.get_weekly_stats(self.user)

        self.assertEqual(stats['challenges_completed'], 0)
        self.assertEqual(stats['xp_earned'], 0)
        self.assertEqual(stats['total_questions'], 0)
        self.assertEqual(stats['correct_answers'], 0)
        self.assertEqual(stats['accuracy'], 0)

    def test_get_lifetime_stats_no_attempts(self):
        """Test lifetime stats returns zeros if no attempts"""
        stats = DailyQuestService.get_lifetime_stats(self.user)

        self.assertEqual(stats['challenges_completed'], 0)
        self.assertEqual(stats['xp_earned'], 0)
        self.assertEqual(stats['total_questions'], 0)
        self.assertEqual(stats['correct_answers'], 0)
        self.assertEqual(stats['accuracy'], 0)

    def test_legacy_generate_quests_for_date_returns_compat_dict(self):
        """Test legacy method returns backward-compatible dict format"""
        test_date = date(2025, 11, 14)

        # Generate quest first
        DailyQuestService.generate_quest_for_user(self.user, test_date)

        # Call legacy method
        result = DailyQuestService.generate_quests_for_date(test_date)

        # Should return dict with expected keys
        self.assertIn('time_quest', result)
        self.assertIn('lesson_quest', result)
        self.assertIsNone(result['time_quest'])
        self.assertIsNotNone(result['lesson_quest'])
