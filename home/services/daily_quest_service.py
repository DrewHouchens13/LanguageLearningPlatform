"""
Service for generating and managing daily quests.
"""
import secrets
from home.models import Lesson, DailyQuest

# Use secrets.SystemRandom() for cryptographically secure random selection
# Even though this is not security-critical (just quiz selection),
# using secrets is better practice and satisfies Bandit security scanner
_random = secrets.SystemRandom()


class DailyQuestService:
    """Service for generating and managing daily quests"""

    @staticmethod
    def generate_quests_for_date(quest_date):
        """
        Generate TWO daily quests for the specified date.
        Returns existing quests if already generated.

        Creates:
        1. Time-based quest: Study for 15 minutes
        2. Lesson-based quest: Complete a specific lesson

        Args:
            quest_date: date object for the quest

        Returns:
            dict: {'time_quest': DailyQuest, 'lesson_quest': DailyQuest}
        """
        # Check if quests already exist for this date
        existing_time = DailyQuest.objects.filter(
            date=quest_date,
            quest_type='study'
        ).first()
        
        existing_lesson = DailyQuest.objects.filter(
            date=quest_date,
            quest_type='quiz'
        ).first()

        # Create missing quests
        if not existing_time:
            existing_time = DailyQuestService._create_study_quest(quest_date)
        
        if not existing_lesson:
            existing_lesson = DailyQuestService._create_quiz_quest(quest_date)

        return {
            'time_quest': existing_time,
            'lesson_quest': existing_lesson
        }

    @staticmethod
    def _create_quiz_quest(quest_date):
        """
        Create a quest to complete a specific lesson quiz.

        Args:
            quest_date: date object for the quest

        Returns:
            DailyQuest instance
        """
        # Select random lesson
        lesson = DailyQuestService._select_random_lesson()

        # Calculate XP reward (same as lesson)
        xp_reward = lesson.xp_value

        # Create quest
        quest = DailyQuest.objects.create(
            date=quest_date,
            title=f"Complete {lesson.title} Lesson",
            description=f"Complete the {lesson.title} quiz to earn {xp_reward} XP!",
            based_on_lesson=lesson,
            quest_type='quiz',
            xp_reward=xp_reward
        )

        return quest

    @staticmethod
    def _create_study_quest(quest_date):
        """
        Create a quest to study for a certain amount of time.

        Args:
            quest_date: date object for the quest

        Returns:
            DailyQuest instance
        """
        # Select random lesson for context (but any lesson can be studied)
        lesson = DailyQuestService._select_random_lesson()

        # Time-based quests award 50 XP
        xp_reward = 50

        # Create quest
        quest = DailyQuest.objects.create(
            date=quest_date,
            title="Study for 15 Minutes",
            description="Complete any lesson quiz to contribute to your study time!",
            based_on_lesson=lesson,
            quest_type='study',
            xp_reward=xp_reward
        )

        return quest

    @staticmethod
    def _select_random_lesson():
        """
        Select a random published lesson.

        Returns:
            Lesson instance

        Raises:
            ValueError: If no published lessons available
        """
        lessons = list(Lesson.objects.filter(is_published=True))
        if not lessons:
            raise ValueError("No published lessons available")

        return _random.choice(lessons)
