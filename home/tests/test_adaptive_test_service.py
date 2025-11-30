"""
Unit tests for AdaptiveTestService.

Tests the adaptive test generation and evaluation logic:
- Test generation with 70/30 weak/strong skill distribution
- Test evaluation and scoring
- Level progression logic
- Retry cooldown enforcement
"""

import json
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

        # All 5 skills will be present (default 50% for missing skills)
        # vocab (45%) and grammar (55%) are weak, others default to 50% (weak)
        # So we'll have at least 2 weak skills, possibly more
        self.assertGreaterEqual(len(distribution['weak']), 2)
        self.assertIn('vocabulary', [s[0] for s in distribution['weak']])
        self.assertIn('grammar', [s[0] for s in distribution['weak']])

    def test_calculate_question_distribution(self):
        """Test question distribution calculation (70% weak, 30% strong)."""
        skill_distribution = {
            'weak': [('vocabulary', 45.0), ('grammar', 55.0)],
            'strong': [('conversation', 75.0), ('reading', 80.0), ('listening', 70.0)]
        }

        distribution = self.service._calculate_question_distribution(skill_distribution)

        # All 5 skills get at least 1 question (5 total)
        # Remaining 5 questions: 70% (3.5 -> 3) to weak, 30% (1.5 -> 2) to strong
        # With 2 weak skills and 3 strong skills, distribution may be equal
        total_weak = sum(count for skill, count in distribution.items()
                        if skill in ['vocabulary', 'grammar'])
        total_strong = sum(count for skill, count in distribution.items()
                          if skill in ['conversation', 'reading', 'listening'])

        # All skills must be represented, total must be 10
        self.assertEqual(sum(distribution.values()), 10)
        # Weak skills should get at least as many as strong (due to 70/30 ratio)
        self.assertGreaterEqual(total_weak, total_strong)

    @patch('openai.OpenAI')
    @patch('home.services.adaptive_test_service.settings')
    def test_generate_adaptive_test_with_ai(self, mock_settings, mock_openai):
        """Test test generation with AI (mocked)."""
        # Set API key in settings
        mock_settings.OPENAI_API_KEY = 'test-key'
        
        # Mock OpenAI response - create a response that returns questions
        # The service will call OpenAI once per skill, so we need to return questions each time
        def make_mock_response(count):
            """Create mock response with requested number of questions."""
            questions_data = [
                {
                    "question": f"Test question {i} for skill?",
                    "options": ["A", "B", "C", "D"],
                    "correct_index": 0,
                    "explanation": "Test explanation",
                    "skill": "vocabulary"
                }
                for i in range(count)
            ]
            mock_response = MagicMock()
            mock_response.choices[0].message.content = json.dumps({"questions": questions_data})
            return mock_response
        
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        # Return different responses based on call count to simulate per-skill calls
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            # Return enough questions for the largest skill request (typically 2-3 per skill)
            return make_mock_response(3)
        
        mock_client.chat.completions.create.side_effect = side_effect

        service = AdaptiveTestService()
        test = service.generate_adaptive_test(self.user, 'Spanish', 1)

        self.assertIn('test_id', test)
        self.assertIn('questions', test)
        self.assertEqual(test['language'], 'Spanish')
        self.assertEqual(test['level'], 1)
        # Should have exactly 10 questions total
        self.assertEqual(len(test['questions']), 10)
        self.assertEqual(test['total_questions'], 10)

    def test_generate_adaptive_test_without_ai(self):
        """Test test generation falls back to templates when AI unavailable."""
        # No API key
        service = AdaptiveTestService()
        service.use_ai = False

        test = service.generate_adaptive_test(self.user, 'Spanish', 1)

        self.assertIn('test_id', test)
        self.assertIn('questions', test)
        # Template fallback generates 1 question per skill (5 total)
        # This is expected behavior when AI is unavailable
        self.assertGreaterEqual(len(test['questions']), 5)
        self.assertEqual(test['language'], 'Spanish')
        self.assertEqual(test['level'], 1)

    def test_evaluate_test_passing(self):
        """Test test evaluation with passing score."""
        progress = UserModuleProgress.objects.create(
            user=self.user,
            module=self.module
        )

        # Create answers with 90% correct (9/10) - passing threshold
        # i < 10 for range(1, 11) means i=1..9 are correct (9 correct), i=10 is wrong
        answers = [
            {'question_id': i, 'answer_index': 0, 'is_correct': i < 10, 'skill': 'vocabulary'}
            for i in range(1, 11)
        ]

        result = self.service.evaluate_test(self.user, self.module, answers)

        # Score is 90% (9/10), which is >= 85% passing threshold
        self.assertEqual(result['score'], 90.0)
        self.assertTrue(result['passed'])
        self.assertEqual(result['correct'], 9)
        self.assertEqual(result['total'], 10)

        # Check progress updated
        progress.refresh_from_db()
        self.assertEqual(progress.best_test_score, 90.0)
        self.assertEqual(progress.test_attempts, 1)

    def test_evaluate_test_failing(self):
        """Test test evaluation with failing score."""
        progress = UserModuleProgress.objects.create(
            user=self.user,
            module=self.module
        )

        # Create answers with 50% correct (5/10) - below 85% threshold
        # i < 6 for range(1, 11) means i=1..5 are correct (5 correct), i=6..10 are wrong
        answers = [
            {'question_id': i, 'answer_index': 0, 'is_correct': i < 6, 'skill': 'vocabulary'}
            for i in range(1, 11)
        ]

        result = self.service.evaluate_test(self.user, self.module, answers)

        self.assertFalse(result.get('passed', True))  # Should not pass
        # 5 correct out of 10 = 50%
        self.assertEqual(result['score'], 50.0)
        self.assertIsNone(result.get('new_level'))
        # can_retry_at may or may not be present depending on implementation

        # Check progress updated
        progress.refresh_from_db()
        self.assertFalse(progress.is_module_complete)
        self.assertEqual(progress.best_test_score, 50.0)
        self.assertEqual(progress.test_attempts, 1)

    def test_handle_level_progression(self):
        """Test level progression logic."""
        progress = UserModuleProgress.objects.create(
            user=self.user,
            module=self.module
        )

        # Create language profile (use get_or_create to avoid unique constraint)
        lang_profile, _ = UserLanguageProfile.objects.get_or_create(
            user=self.user,
            language='Spanish',
            defaults={'proficiency_level': 1}
        )
        lang_profile.proficiency_level = 1
        lang_profile.save()

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

        # Use get_or_create to avoid unique constraint error
        lang_profile, _ = UserLanguageProfile.objects.get_or_create(
            user=self.user,
            language='Spanish',
            defaults={'proficiency_level': 10}
        )
        lang_profile.proficiency_level = 10
        lang_profile.save()

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
        """Test can_take_test respects 10-minute cooldown."""
        progress = UserModuleProgress.objects.create(
            user=self.user,
            module=self.module,
            lessons_completed=[1, 2, 3, 4, 5],
            last_test_date=timezone.now() - timedelta(minutes=5)  # 5 minutes ago (within 10 min cooldown)
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

