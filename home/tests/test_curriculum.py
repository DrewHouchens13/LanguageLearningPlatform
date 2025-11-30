"""
Unit tests for curriculum models and progress tracking.

Tests the new adaptive curriculum system models:
- SkillCategory
- LearningModule
- UserModuleProgress
- UserSkillMastery
- UserQuestionAttempt
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from home.models import (
    LearningModule,
    Lesson,
    SkillCategory,
    UserModuleProgress,
    UserQuestionAttempt,
    UserSkillMastery,
)


class TestSkillCategory(TestCase):
    """Test SkillCategory model."""

    def setUp(self):
        """Set up test data."""
        # Skill categories are seeded by migration
        self.vocab = SkillCategory.objects.get(name='vocabulary')
        self.grammar = SkillCategory.objects.get(name='grammar')

    def test_skill_category_str(self):
        """Test string representation."""
        # SkillCategory includes emoji in __str__
        self.assertIn('Vocabulary', str(self.vocab))
        # Check it starts with emoji
        self.assertTrue(str(self.vocab).startswith('📚'))

    def test_skill_category_choices(self):
        """Test skill category has valid choices."""
        valid_skills = ['vocabulary', 'grammar', 'conversation', 'reading', 'listening']
        for skill_name in valid_skills:
            skill = SkillCategory.objects.get(name=skill_name)
            self.assertIn(skill.name, [choice[0] for choice in SkillCategory.SKILL_CHOICES])


class TestLearningModule(TestCase):
    """Test LearningModule model."""

    def setUp(self):
        """Set up test data."""
        self.module = LearningModule.objects.create(
            language='Spanish',
            proficiency_level=1,
            name='Basics',
            description='Basic Spanish vocabulary and grammar',
            passing_score=85
        )

    def test_learning_module_str(self):
        """Test string representation."""
        self.assertEqual(str(self.module), 'Spanish Level 1: Basics')

    def test_learning_module_unique_constraint(self):
        """Test that language + level combination is unique."""
        from django.db import IntegrityError, transaction

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                LearningModule.objects.create(
                    language='Spanish',
                    proficiency_level=1,
                    name='Duplicate'
                )

    def test_get_lessons(self):
        """Test get_lessons returns lessons in skill order."""
        # Create skill categories
        vocab = SkillCategory.objects.get(name='vocabulary')
        grammar = SkillCategory.objects.get(name='grammar')

        # Create lessons
        lesson1 = Lesson.objects.create(
            title='Vocab Lesson',
            slug='spanish-level-1-vocabulary',
            language='Spanish',
            difficulty_level=1,
            skill_category=vocab,
            is_published=True
        )
        lesson2 = Lesson.objects.create(
            title='Grammar Lesson',
            slug='spanish-level-1-grammar',
            language='Spanish',
            difficulty_level=1,
            skill_category=grammar,
            is_published=True
        )

        lessons = self.module.get_lessons()
        self.assertEqual(lessons.count(), 2)
        # Should be ordered by skill_category.order
        self.assertEqual(lessons[0].skill_category.order, vocab.order)
        self.assertEqual(lessons[1].skill_category.order, grammar.order)


class TestUserModuleProgress(TestCase):
    """Test UserModuleProgress model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.module = LearningModule.objects.create(
            language='Spanish',
            proficiency_level=1,
            name='Basics'
        )
        self.progress = UserModuleProgress.objects.create(
            user=self.user,
            module=self.module
        )

    def test_user_module_progress_str(self):
        """Test string representation."""
        self.assertIn('testuser', str(self.progress))
        self.assertIn('Spanish Level 1', str(self.progress))

    def test_all_lessons_completed(self):
        """Test all_lessons_completed method."""
        self.assertFalse(self.progress.all_lessons_completed())

        # Add 5 lesson IDs
        self.progress.lessons_completed = [1, 2, 3, 4, 5]
        self.progress.save()
        self.assertTrue(self.progress.all_lessons_completed())

    def test_can_take_test(self):
        """Test can_take_test method."""
        self.assertFalse(self.progress.can_take_test())

        self.progress.lessons_completed = [1, 2, 3, 4, 5]
        self.progress.save()
        self.assertTrue(self.progress.can_take_test())

    def test_can_retry_test(self):
        """Test can_retry_test respects 10-minute cooldown."""
        # No previous attempt
        self.assertTrue(self.progress.can_retry_test())

        # Recent attempt (less than 10 minutes)
        self.progress.last_test_date = timezone.now() - timedelta(minutes=5)
        self.progress.save()
        self.assertFalse(self.progress.can_retry_test())

        # Old attempt (more than 10 minutes)
        self.progress.last_test_date = timezone.now() - timedelta(minutes=15)
        self.progress.save()
        self.assertTrue(self.progress.can_retry_test())

    def test_mark_lesson_complete(self):
        """Test mark_lesson_complete adds lesson ID."""
        self.assertEqual(len(self.progress.lessons_completed), 0)

        self.progress.mark_lesson_complete(1)
        self.assertEqual(len(self.progress.lessons_completed), 1)
        self.assertIn(1, self.progress.lessons_completed)

        # Should not duplicate
        self.progress.mark_lesson_complete(1)
        self.assertEqual(len(self.progress.lessons_completed), 1)

    def test_unique_user_module_constraint(self):
        """Test that user + module combination is unique."""
        from django.db import IntegrityError, transaction

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                UserModuleProgress.objects.create(
                    user=self.user,
                    module=self.module
                )


class TestUserSkillMastery(TestCase):
    """Test UserSkillMastery model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.vocab = SkillCategory.objects.get(name='vocabulary')

    def test_user_skill_mastery_str(self):
        """Test string representation."""
        mastery = UserSkillMastery.objects.create(
            user=self.user,
            skill_category=self.vocab,
            language='Spanish',
            mastery_percentage=75.5
        )
        self.assertIn('testuser', str(mastery))
        self.assertIn('vocabulary', str(mastery))

    def test_unique_user_skill_language_constraint(self):
        """Test that user + skill + language combination is unique."""
        from django.db import IntegrityError, transaction

        UserSkillMastery.objects.create(
            user=self.user,
            skill_category=self.vocab,
            language='Spanish',
            mastery_percentage=50.0
        )

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                UserSkillMastery.objects.create(
                    user=self.user,
                    skill_category=self.vocab,
                    language='Spanish',
                    mastery_percentage=60.0
                )


class TestUserQuestionAttempt(TestCase):
    """Test UserQuestionAttempt model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.vocab = SkillCategory.objects.get(name='vocabulary')
        self.lesson = Lesson.objects.create(
            title='Test Lesson',
            slug='test-lesson',
            language='Spanish',
            difficulty_level=1,
            skill_category=self.vocab,
            is_published=True
        )
        from home.models import LessonQuizQuestion
        self.question = LessonQuizQuestion.objects.create(
            lesson=self.lesson,
            question='Test question?',
            options=['A', 'B', 'C', 'D'],
            correct_index=0
        )

    def test_user_question_attempt_creation(self):
        """Test creating a question attempt."""
        attempt = UserQuestionAttempt.objects.create(
            user=self.user,
            question=self.question,
            skill_category=self.vocab,
            is_correct=True,
            time_taken_seconds=5
        )
        self.assertEqual(attempt.user, self.user)
        self.assertEqual(attempt.question, self.question)
        self.assertTrue(attempt.is_correct)
        self.assertEqual(attempt.time_taken_seconds, 5)

