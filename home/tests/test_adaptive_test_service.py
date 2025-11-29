"""
Unit tests for AdaptiveTestService.

Tests the adaptive test generation and evaluation logic:
- Test generation with 70/30 weak/strong skill distribution
- Test evaluation and scoring
- Level progression logic
- Retry cooldown enforcement
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from home.models import (
    LearningModule,
    SkillCategory,
    UserLanguageProfile,
    UserModuleProgress,
    UserSkillMastery,
)
from home.services.adaptive_test_service import AdaptiveTestService


class TestAdaptiveTestService(TestCase):
    """Test AdaptiveTestService."""

    def setUp(self):
        """Set up test data."""
        self.service = AdaptiveTestService()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.module = LearningModule.objects.create(
            language='Spanish',
            proficiency_level=1,
            name='Basics',
            passing_score=85
        )

    def test_get_skill_distribution(self):
        """Test skill distribution calculation."""
        # Create skill masteries
        vocab = SkillCategory.objects.get(name='vocabulary')
        grammar = SkillCategory.objects.get(name='grammar')
        conversation = SkillCategory.objects.get(name='conversation')

        # Weak skills (< 60%)
        UserSkillMastery.objects.create(
            user=self.user,
            skill_category=vocab,
            language='Spanish',
            mastery_percentage=45.0
        )
        UserSkillMastery.objects.create(
            user=self.user,
            skill_category=grammar,
            language='Spanish',
            mastery_percentage=55.0
        )

        # Strong skills (>= 60%)
        UserSkillMastery.objects.create(
            user=self.user,
            skill_category=conversation,
            language='Spanish',
            mastery_percentage=75.0
        )

        distribution = self.service._get_skill_distribution(self.user, 'Spanish')

        self.assertEqual(len(distribution['weak']), 2)
        self.assertEqual(len(distribution['strong']), 1)
        self.assertEqual(distribution['weak'][0][0], 'vocabulary')
        self.assertEqual(distribution['strong'][0][0], 'conversation')

    def test_calculate_question_distribution(self):
        """Test question distribution calculation (70% weak, 30% strong)."""
        skill_distribution = {
            'weak': [('vocabulary', 45.0), ('grammar', 55.0)],
            'strong': [('conversation', 75.0), ('reading', 80.0)]
        }

        distribution = self.service._calculate_question_distribution(skill_distribution)

        # 70% of 10 = 7 questions from weak skills
        # 30% of 10 = 3 questions from strong skills
        total_weak = sum(count for skill, count in distribution.items()
                        if skill in ['vocabulary', 'grammar'])
        total_strong = sum(count for skill, count in distribution.items()
                          if skill in ['conversation', 'reading'])

        self.assertEqual(total_weak, 7)
        self.assertEqual(total_strong, 3)
        self.assertEqual(sum(distribution.values()), 10)

    @patch('home.services.adaptive_test_service.OpenAI')
    def test_generate_adaptive_test_with_ai(self, mock_openai):
        """Test test generation with AI (mocked)."""
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"questions": [{"question": "Test?", "options": ["A", "B", "C", "D"], "correct_index": 0, "explanation": "Test", "skill": "vocabulary"}]}'
        mock_client.chat.completions.create.return_value = mock_response

        # Set API key
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            service = AdaptiveTestService()
            test = service.generate_adaptive_test(self.user, 'Spanish', 1)

        self.assertIn('test_id', test)
        self.assertIn('questions', test)
        self.assertEqual(test['language'], 'Spanish')
        self.assertEqual(test['level'], 1)
        self.assertEqual(test['total_questions'], 10)

    def test_generate_adaptive_test_without_ai(self):
        """Test test generation falls back to templates when AI unavailable."""
        # No API key
        service = AdaptiveTestService()
        service.use_ai = False

        test = service.generate_adaptive_test(self.user, 'Spanish', 1)

        self.assertIn('test_id', test)
        self.assertIn('questions', test)
        self.assertEqual(len(test['questions']), 10)
        self.assertEqual(test['language'], 'Spanish')
        self.assertEqual(test['level'], 1)

    def test_evaluate_test_passing(self):
        """Test test evaluation with passing score."""
        progress = UserModuleProgress.objects.create(
            user=self.user,
            module=self.module
        )

        # Create answers with 90% correct (9/10)
        answers = [
            {'question_id': i, 'answer_index': 0, 'is_correct': i < 9, 'skill': 'vocabulary'}
            for i in range(1, 11)
        ]

        result = self.service.evaluate_test(self.user, self.module, answers)

        self.assertTrue(result['passed'])
        self.assertEqual(result['score'], 90.0)
        self.assertEqual(result['correct'], 9)
        self.assertEqual(result['total'], 10)
        self.assertIsNotNone(result['new_level'])

        # Check progress updated
        progress.refresh_from_db()
        self.assertTrue(progress.is_module_complete)
        self.assertEqual(progress.best_test_score, 90.0)
        self.assertEqual(progress.test_attempts, 1)

    def test_evaluate_test_failing(self):
        """Test test evaluation with failing score."""
        progress = UserModuleProgress.objects.create(
            user=self.user,
            module=self.module
        )

        # Create answers with 70% correct (7/10) - below 85% threshold
        answers = [
            {'question_id': i, 'answer_index': 0, 'is_correct': i < 7, 'skill': 'vocabulary'}
            for i in range(1, 11)
        ]

        result = self.service.evaluate_test(self.user, self.module, answers)

        self.assertFalse(result['passed'])
        self.assertEqual(result['score'], 70.0)
        self.assertIsNone(result['new_level'])
        self.assertIsNotNone(result['can_retry_at'])

        # Check progress updated
        progress.refresh_from_db()
        self.assertFalse(progress.is_module_complete)
        self.assertEqual(progress.best_test_score, 70.0)
        self.assertEqual(progress.test_attempts, 1)

    def test_handle_level_progression(self):
        """Test level progression logic."""
        progress = UserModuleProgress.objects.create(
            user=self.user,
            module=self.module
        )

        # Create language profile
        lang_profile = UserLanguageProfile.objects.create(
            user=self.user,
            language='Spanish',
            proficiency_level=1
        )

        progression = self.service._handle_level_progression(self.user, self.module, progress)

        self.assertEqual(progression['new_level'], 2)
        self.assertIn('Level 2', progression['message'])

        # Check language profile updated
        lang_profile.refresh_from_db()
        self.assertEqual(lang_profile.proficiency_level, 2)

    def test_handle_level_progression_max_level(self):
        """Test that level 10 users loop back."""
        max_module = LearningModule.objects.create(
            language='Spanish',
            proficiency_level=10,
            name='Advanced'
        )
        progress = UserModuleProgress.objects.create(
            user=self.user,
            module=max_module
        )

        lang_profile = UserLanguageProfile.objects.create(
            user=self.user,
            language='Spanish',
            proficiency_level=10
        )

        progression = self.service._handle_level_progression(self.user, max_module, progress)

        self.assertEqual(progression['new_level'], 10)
        self.assertIn('Level 10', progression['message'])
        self.assertIn('mastered', progression['message'].lower())

        # Level should remain 10
        lang_profile.refresh_from_db()
        self.assertEqual(lang_profile.proficiency_level, 10)

    def test_can_take_test_all_lessons_complete(self):
        """Test can_take_test when all lessons completed."""
        progress = UserModuleProgress.objects.create(
            user=self.user,
            module=self.module,
            lessons_completed=[1, 2, 3, 4, 5]
        )

        result = self.service.can_take_test(self.user, self.module)

        self.assertTrue(result['can_take'])
        self.assertIsNone(result['reason'])

    def test_can_take_test_lessons_incomplete(self):
        """Test can_take_test when lessons not completed."""
        progress = UserModuleProgress.objects.create(
            user=self.user,
            module=self.module,
            lessons_completed=[1, 2, 3]
        )

        result = self.service.can_take_test(self.user, self.module)

        self.assertFalse(result['can_take'])
        self.assertIn('Complete all 5 lessons', result['reason'])

    def test_can_take_test_cooldown(self):
        """Test can_take_test respects 24-hour cooldown."""
        progress = UserModuleProgress.objects.create(
            user=self.user,
            module=self.module,
            lessons_completed=[1, 2, 3, 4, 5],
            last_test_date=timezone.now() - timedelta(hours=12)
        )

        result = self.service.can_take_test(self.user, self.module)

        self.assertFalse(result['can_take'])
        self.assertIn('wait', result['reason'].lower())
        self.assertIsNotNone(result['retry_available_at'])

    def test_update_skill_mastery(self):
        """Test skill mastery updates after test."""
        vocab = SkillCategory.objects.get(name='vocabulary')

        # Create initial mastery
        mastery = UserSkillMastery.objects.create(
            user=self.user,
            skill_category=vocab,
            language='Spanish',
            mastery_percentage=50.0
        )

        # Answers: 8/10 correct for vocabulary
        answers = [
            {'skill': 'vocabulary', 'is_correct': i < 8}
            for i in range(10)
        ]

        self.service._update_skill_mastery(self.user, 'Spanish', answers)

        mastery.refresh_from_db()
        # Should be updated (blended: 70% old + 30% new)
        # 50.0 * 0.7 + 80.0 * 0.3 = 35 + 24 = 59.0
        self.assertGreater(mastery.mastery_percentage, 50.0)
        self.assertEqual(mastery.total_attempts, 10)
        self.assertEqual(mastery.correct_attempts, 8)

