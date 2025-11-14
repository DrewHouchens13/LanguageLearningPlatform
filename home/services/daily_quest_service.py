"""
Service for generating and managing daily quests.

🤖 AI ASSISTANT INSTRUCTIONS - DAILY QUEST SYSTEM
================================================================================

PURPOSE:
This service implements a personalized daily challenge system where users receive
ONE quest per day with 5 random questions from their completed or available lessons.

ARCHITECTURE OVERVIEW:
1. ONE quest per day (not multiple quests)
2. 5 questions per quest (randomly selected)
3. Personalized question selection based on user progress
4. Question snapshots stored in DailyQuestQuestion (not FK references)
5. XP rewards based on performance

KEY CONCEPTS:

1. QUESTION SELECTION LOGIC (Smart Personalization):
   - IF user has completed ANY lessons → Questions from COMPLETED lessons only
   - IF user has NOT completed any lessons → Questions from ALL available lessons
   - This ensures users get relevant questions based on their learning progress

2. QUESTION SNAPSHOTS (Data Isolation):
   - Questions are COPIED (not referenced) to DailyQuestQuestion model
   - Stores: question_text, options (JSON), correct_index
   - Why? Prevents issues if original lesson questions are edited/deleted
   - Each quest is a snapshot in time, preserving data integrity

3. ONE QUEST PER DAY:
   - Quest is identified by date (YYYY-MM-DD)
   - Same quest for all users on the same day
   - New quest generated automatically each day

4. XP CALCULATION:
   - Base XP: 50 per quest
   - Bonus: +10 per correct answer (max 50 bonus)
   - Perfect score: 100 XP (50 base + 50 bonus)

DATABASE MODELS USED:
- DailyQuest: One record per date (date, xp_reward, is_active)
- DailyQuestQuestion: 5 records per quest (snapshots of questions)
- LessonCompletion: Tracks which lessons user has completed
- LessonQuizQuestion: Source of questions (copied to DailyQuestQuestion)
- UserDailyQuestAttempt: Tracks user attempts and scores

HOW TO EXTEND FOR OTHER LANGUAGES:
1. Create lessons in new language (e.g., French)
2. Add quiz questions to those lessons
3. System automatically includes them in question pool
4. NO code changes needed!

EXAMPLE - Adding French:
1. Create French lessons: Lesson.objects.create(language='French', ...)
2. Add quiz questions: LessonQuizQuestion.objects.create(lesson=french_lesson, ...)
3. When user completes French lesson, questions automatically enter their pool
4. Daily quest will include mix of all completed language lessons

KEY METHODS:
- generate_quest_for_user(): Creates daily quest with 5 questions
- _get_user_question_pool(): Gets personalized question pool
- submit_quest(): Processes user's answers and calculates score/XP
- get_weekly_stats(): Returns weekly performance statistics

RELATED FILES:
- home/models.py (DailyQuest, DailyQuestQuestion, UserDailyQuestAttempt)
- home/views.py (daily_quest_view, daily_quest_submit)
- home/templates/home/daily_quest.html (Quest display template)

TESTING:
- See tests/test_daily_quest.py for comprehensive test coverage
- 23 tests covering all logic paths and edge cases

================================================================================
"""
import secrets
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from home.models import (
    DailyQuest,
    DailyQuestQuestion,
    LessonCompletion,
    LessonQuizQuestion,
    UserDailyQuestAttempt,
)

# Use secrets.SystemRandom() for cryptographically secure random selection
_random = secrets.SystemRandom()


class DailyQuestService:
    """Service for generating and managing daily quests"""

    @staticmethod
    def generate_quest_for_user(user, quest_date):
        """
        Generate ONE daily quest with 5 random questions for the user.

        Question Selection Logic:
        - If user has completed ANY lessons: Pull from completed lessons only
        - If user has NOT completed any lessons: Pull from all available lessons

        Args:
            user: User instance
            quest_date: date object for the quest

        Returns:
            DailyQuest instance with 5 DailyQuestQuestion records

        Raises:
            ValueError: If insufficient questions available
        """
        # Check if quest already exists for this date
        existing_quest = DailyQuest.objects.filter(date=quest_date).first()
        if existing_quest:
            return existing_quest

        # Get personalized question pool
        question_pool = DailyQuestService._get_user_question_pool(user)

        if len(question_pool) < 5:
            raise ValueError(f"Insufficient questions available. Need 5, found {len(question_pool)}")

        # Select 5 random questions
        selected_questions = _random.sample(list(question_pool), 5)

        # Pick a lesson to represent this quest (use first question's lesson)
        representative_lesson = selected_questions[0].lesson

        # Create the quest
        quest = DailyQuest.objects.create(
            date=quest_date,
            title="Daily Challenge",
            description="Answer 5 questions to earn XP!",
            based_on_lesson=representative_lesson,
            quest_type='quiz',
            xp_reward=50
        )

        # Create DailyQuestQuestion records from LessonQuizQuestion
        for idx, lesson_q in enumerate(selected_questions, start=1):
            DailyQuestQuestion.objects.create(
                daily_quest=quest,
                question_text=lesson_q.question,
                options=lesson_q.options,
                correct_index=lesson_q.correct_index,
                order=idx,
                difficulty_level='medium'
            )

        return quest

    @staticmethod
    def _get_user_question_pool(user):
        """
        Get personalized question pool for user based on their progress.

        Logic:
        - If user has completed ANY lessons: Questions from completed lessons only
        - If user has NOT completed any lessons: Questions from all published lessons

        Args:
            user: User instance

        Returns:
            QuerySet of LessonQuizQuestion objects
        """
        # Check if user has completed any lessons
        completed_lesson_ids = LessonCompletion.objects.filter(
            user=user
        ).distinct().values_list('lesson_id', flat=True)

        if completed_lesson_ids:
            # User has completed lessons - pull from those only
            # Convert string IDs to integers for comparison
            lesson_ids = [int(lid) for lid in completed_lesson_ids]
            question_pool = LessonQuizQuestion.objects.filter(
                lesson__id__in=lesson_ids
            )
        else:
            # User hasn't completed any lessons - pull from all published lessons
            question_pool = LessonQuizQuestion.objects.filter(
                lesson__is_published=True
            )

        return question_pool

    @staticmethod
    def calculate_quest_score(quest, submitted_answers):
        """
        Calculate score for a quest submission.

        Args:
            quest: DailyQuest instance
            submitted_answers: dict mapping question IDs to submitted answer indices (as strings)

        Returns:
            tuple: (correct_count, total_questions, xp_earned)
        """
        questions = DailyQuestQuestion.objects.filter(daily_quest=quest)
        total_questions = questions.count()
        correct_count = 0

        for question in questions:
            submitted_idx_str = submitted_answers.get(str(question.id), '')

            try:
                submitted_idx = int(submitted_idx_str)
                if submitted_idx == question.correct_index:
                    correct_count += 1
            except (ValueError, TypeError):
                # Invalid submission, counts as wrong
                pass

        # XP proportional to correct answers
        if total_questions > 0:
            xp_earned = int((correct_count / total_questions) * quest.xp_reward)
        else:
            xp_earned = 0

        return correct_count, total_questions, xp_earned

    @staticmethod
    def get_weekly_stats(user):
        """
        Get weekly Daily Challenge statistics for user.

        Args:
            user: User instance

        Returns:
            dict: {
                'challenges_completed': int,
                'xp_earned': int,
                'total_questions': int,
                'correct_answers': int,
                'accuracy': float
            }
        """
        week_ago = timezone.now() - timedelta(days=7)

        weekly_attempts = UserDailyQuestAttempt.objects.filter(
            user=user,
            is_completed=True,
            completed_at__gte=week_ago
        )

        stats = weekly_attempts.aggregate(
            total_xp=Sum('xp_earned'),
            total_questions=Sum('total_questions'),
            total_correct=Sum('correct_answers')
        )

        return {
            'challenges_completed': weekly_attempts.count(),
            'xp_earned': stats['total_xp'] or 0,
            'total_questions': stats['total_questions'] or 0,
            'correct_answers': stats['total_correct'] or 0,
            'accuracy': DailyQuestService._calculate_accuracy(
                stats['total_correct'],
                stats['total_questions']
            )
        }

    @staticmethod
    def get_lifetime_stats(user):
        """
        Get lifetime Daily Challenge statistics for user.

        Args:
            user: User instance

        Returns:
            dict: {
                'challenges_completed': int,
                'xp_earned': int,
                'total_questions': int,
                'correct_answers': int,
                'accuracy': float
            }
        """
        all_attempts = UserDailyQuestAttempt.objects.filter(
            user=user,
            is_completed=True
        )

        stats = all_attempts.aggregate(
            total_xp=Sum('xp_earned'),
            total_questions=Sum('total_questions'),
            total_correct=Sum('correct_answers')
        )

        return {
            'challenges_completed': all_attempts.count(),
            'xp_earned': stats['total_xp'] or 0,
            'total_questions': stats['total_questions'] or 0,
            'correct_answers': stats['total_correct'] or 0,
            'accuracy': DailyQuestService._calculate_accuracy(
                stats['total_correct'],
                stats['total_questions']
            )
        }

    @staticmethod
    def _calculate_accuracy(correct, total):
        """
        Calculate accuracy percentage (DRY helper).

        Args:
            correct: Number of correct answers
            total: Total number of questions

        Returns:
            float: Accuracy percentage (0-100)
        """
        return (correct / total * 100) if total and total > 0 else 0

    # LEGACY COMPATIBILITY METHOD (for old code that expects 2 quests)
    @staticmethod
    def generate_quests_for_date(quest_date):
        """
        Legacy method for backward compatibility.
        Now generates a single quest but returns dict format expected by old code.

        Args:
            quest_date: date object for the quest

        Returns:
            dict: {'time_quest': None, 'lesson_quest': quest}
        """
        quest = DailyQuest.objects.filter(date=quest_date).first()

        return {
            'time_quest': None,  # No longer used
            'lesson_quest': quest  # Single quest
        }
