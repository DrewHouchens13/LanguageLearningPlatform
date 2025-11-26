"""
Comprehensive tests for XP and Leveling System (Sprint 3 - Issue #17).

Tests cover:
- XP calculation formulas
- Level progression
- XP awarding logic
- Level-up detection
- Integration with lesson completion
"""

from django.contrib.auth.models import User
from django.test import TestCase

from home.models import Lesson, UserProfile


class TestXPCalculations(TestCase):
    """Test XP calculation methods."""

    def test_get_xp_for_level_1(self):
        """Level 1 requires 0 XP."""
        self.assertEqual(UserProfile.get_xp_for_level(1), 0)

    def test_get_xp_for_level_2(self):
        """Level 2 requires 100 XP."""
        self.assertEqual(UserProfile.get_xp_for_level(2), 100)

    def test_get_xp_for_level_3(self):
        """Level 3 requires 282 XP (100 * 2^1.5 = 282.84)."""
        xp = UserProfile.get_xp_for_level(3)
        self.assertTrue(280 <= xp <= 285, f"XP {xp} not in expected range 280-285")

    def test_get_xp_for_level_progression(self):
        """XP requirements increase progressively."""
        levels = [UserProfile.get_xp_for_level(i) for i in range(1, 11)]
        # Verify strictly increasing
        for i in range(len(levels) - 1):
            self.assertLess(levels[i], levels[i + 1])

    def test_get_xp_for_negative_level(self):
        """Negative level returns 0 XP."""
        self.assertEqual(UserProfile.get_xp_for_level(-1), 0)
        self.assertEqual(UserProfile.get_xp_for_level(0), 0)


class TestLevelCalculations(TestCase):
    """Test level calculation from XP."""

    def setUp(self):
        """Create test user and profile."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile

    def test_initial_level_is_1(self):
        """New user starts at level 1."""
        self.assertEqual(self.profile.current_level, 1)
        self.assertEqual(self.profile.total_xp, 0)

    def test_calculate_level_from_zero_xp(self):
        """0 XP = Level 1."""
        self.profile.total_xp = 0
        self.assertEqual(self.profile.calculate_level_from_xp(), 1)

    def test_calculate_level_from_50_xp(self):
        """50 XP = Level 1 (under 100 threshold)."""
        self.profile.total_xp = 50
        self.assertEqual(self.profile.calculate_level_from_xp(), 1)

    def test_calculate_level_from_100_xp(self):
        """100 XP = Level 2 (exactly at threshold)."""
        self.profile.total_xp = 100
        assert self.profile.calculate_level_from_xp() == 2

    def test_calculate_level_from_200_xp(self):
        """200 XP = Level 2 (between 100-282)."""
        self.profile.total_xp = 200
        assert self.profile.calculate_level_from_xp() == 2

    def test_calculate_level_from_500_xp(self):
        """500 XP = Level 4 or higher."""
        self.profile.total_xp = 500
        level = self.profile.calculate_level_from_xp()
        assert level >= 3  # Should be level 3 or 4

    def test_calculate_level_from_1000_xp(self):
        """1000 XP = Higher level."""
        self.profile.total_xp = 1000
        level = self.profile.calculate_level_from_xp()
        assert level >= 5


class TestXPToNextLevel(TestCase):
    """Test XP to next level calculations."""

    def setUp(self):
        """Create test user and profile."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile

    def test_xp_to_next_level_at_level_1(self):
        """At level 1 with 0 XP, need 100 XP for level 2."""
        self.profile.total_xp = 0
        self.profile.current_level = 1
        assert self.profile.get_xp_to_next_level() == 100

    def test_xp_to_next_level_partial_progress(self):
        """With 50/100 XP, need 50 more for level 2."""
        self.profile.total_xp = 50
        self.profile.current_level = 1
        assert self.profile.get_xp_to_next_level() == 50

    def test_xp_to_next_level_at_threshold(self):
        """At level threshold, need XP for next level."""
        self.profile.total_xp = 100
        self.profile.current_level = 2
        xp_needed = self.profile.get_xp_to_next_level()
        assert xp_needed > 0  # Need more XP for level 3


class TestProgressToNextLevel(TestCase):
    """Test progress percentage calculations."""

    def setUp(self):
        """Create test user and profile."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile

    def test_progress_at_zero_xp(self):
        """At 0 XP (level 1), progress is 0%."""
        self.profile.total_xp = 0
        self.profile.current_level = 1
        progress = self.profile.get_progress_to_next_level()
        assert progress == 0.0

    def test_progress_at_halfway(self):
        """At 50/100 XP, progress is 50%."""
        self.profile.total_xp = 50
        self.profile.current_level = 1
        progress = self.profile.get_progress_to_next_level()
        assert 49 <= progress <= 51  # Allow for rounding

    def test_progress_at_threshold(self):
        """At level threshold, progress should be 0% toward next."""
        self.profile.total_xp = 100
        self.profile.current_level = 2
        progress = self.profile.get_progress_to_next_level()
        assert 0 <= progress <= 5  # Should be close to 0

    def test_progress_never_exceeds_100(self):
        """Progress percentage never exceeds 100%."""
        self.profile.total_xp = 10000
        self.profile.current_level = 1
        progress = self.profile.get_progress_to_next_level()
        assert progress <= 100.0


class TestAwardXP(TestCase):
    """Test XP awarding functionality."""

    def setUp(self):
        """Create test user and profile."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile
        # Refresh to ensure we have current state
        self.profile.refresh_from_db()

    def test_award_positive_xp(self):
        """Awarding XP increases total_xp."""
        result = self.profile.award_xp(50)
        assert result['xp_awarded'] == 50
        assert result['total_xp'] == 50
        assert self.profile.total_xp == 50

    def test_award_zero_xp(self):
        """Awarding 0 XP does nothing."""
        result = self.profile.award_xp(0)
        assert result['xp_awarded'] == 0
        assert result['total_xp'] == 0
        assert result['leveled_up'] is False

    def test_award_negative_xp(self):
        """Awarding negative XP raises ValueError."""
        import pytest
        with pytest.raises(ValueError, match="XP amount must be non-negative"):
            self.profile.award_xp(-50)

    def test_award_xp_no_level_up(self):
        """Awarding XP without level up."""
        result = self.profile.award_xp(50)
        assert result['leveled_up'] is False
        assert result['new_level'] is None
        assert result['old_level'] == 1
        self.assertEqual(self.profile.current_level, 1)

    def test_award_xp_triggers_level_up(self):
        """Awarding 100 XP triggers level up from 1 to 2."""
        result = self.profile.award_xp(100)
        assert result['leveled_up'] is True
        assert result['old_level'] == 1
        assert result['new_level'] == 2
        self.assertEqual(self.profile.current_level, 2)

    def test_award_xp_multiple_level_ups(self):
        """Awarding enough XP can skip multiple levels."""
        result = self.profile.award_xp(1000)
        assert result['leveled_up'] is True
        assert result['old_level'] == 1
        assert result['new_level'] >= 5  # Should reach at least level 5

    def test_award_xp_cumulative(self):
        """Multiple XP awards accumulate correctly."""
        self.profile.award_xp(40)
        self.profile.award_xp(40)
        result = self.profile.award_xp(20)

        assert self.profile.total_xp == 100
        assert result['leveled_up'] is True  # Should level up at 100
        self.assertEqual(self.profile.current_level, 2)

    def test_award_xp_persists_to_database(self):
        """Awarded XP is saved to database."""
        self.profile.award_xp(75)

        # Refresh from database
        self.profile.refresh_from_db()
        assert self.profile.total_xp == 75
        self.assertEqual(self.profile.current_level, 1)


class TestXPIntegrationWithLessons(TestCase):
    """Test XP awarding integration with lesson completion."""

    def setUp(self):
        """Create test user, profile, and lesson."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile

        self.lesson = Lesson.objects.create(
            title='Test Lesson',
            slug='test-lesson',
            description='Test lesson for XP',
            language='Spanish',
            difficulty_level='A1'
        )

    def test_lesson_completion_awards_xp(self):
        """Completing a lesson should award XP (via views.py integration)."""
        # This tests that the mechanism exists
        # Actual integration is tested via view tests
        initial_xp = self.profile.total_xp

        # Award XP as lesson completion would
        self.profile.award_xp(50)  # Base XP

        self.assertEqual(self.profile.total_xp, initial_xp + 50)

    def test_perfect_quiz_bonus_xp(self):
        """Perfect quiz score should award bonus XP."""
        # Award base + bonus (as implemented in views.py)
        base_xp = 50
        bonus_xp = 10

        result = self.profile.award_xp(base_xp + bonus_xp)

        self.assertEqual(result['xp_awarded'], 60)
        self.assertEqual(self.profile.total_xp, 60)

    def test_multiple_lesson_completions(self):
        """Completing multiple lessons accumulates XP."""
        # Complete 3 lessons
        for _ in range(3):
            self.profile.award_xp(50)

        self.assertEqual(self.profile.total_xp, 150)
        self.assertEqual(self.profile.current_level, 2)  # Should level up at 100


class TestXPEdgeCases(TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        """Create test user and profile."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile

    def test_level_up_at_exact_threshold(self):
        """Level up occurs at exact threshold."""
        self.profile.award_xp(100)  # Exact threshold
        self.assertEqual(self.profile.current_level, 2)

    def test_level_up_one_xp_over_threshold(self):
        """Level up occurs even 1 XP over threshold."""
        self.profile.award_xp(101)
        self.assertEqual(self.profile.current_level, 2)

    def test_level_up_one_xp_under_threshold(self):
        """No level up if 1 XP under threshold."""
        self.profile.award_xp(99)
        self.assertEqual(self.profile.current_level, 1)

    def test_very_high_xp(self):
        """System rejects unreasonably high XP values."""
        import pytest
        with pytest.raises(ValueError, match="exceeds maximum allowed"):
            self.profile.award_xp(1000000)

    def test_award_xp_after_manual_level_change(self):
        """System recovers if level is manually set incorrectly."""
        # Manually set wrong level
        self.profile.total_xp = 150
        self.profile.current_level = 1  # Wrong! Should be 2
        self.profile.save()

        # Award XP should recalculate correct level
        _result = self.profile.award_xp(50)  # pylint: disable=unused-variable

        # Should detect we're at wrong level and fix it
        self.assertGreaterEqual(self.profile.current_level, 2)
