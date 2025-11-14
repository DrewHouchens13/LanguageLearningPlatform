"""
Service for generating and managing daily quests.
"""
import secrets
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from home.models import Lesson, DailyQuest, DailyQuestQuestion, UserDailyQuestAttempt, LessonProgress

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

        # Create the quest
        quest = DailyQuest.objects.create(
            date=quest_date,
            title="Daily Challenge",
            description="Answer 5 questions to earn XP!",
            quest_type='quiz',
            xp_reward=50
        )

        # Create DailyQuestQuestion records
        for question in selected_questions:
            DailyQuestQuestion.objects.create(
                quest=quest,
                lesson=question.lesson,
                question_text=question.question_text,
                correct_answer=question.correct_answer,
                option_a=question.option_a,
                option_b=question.option_b,
                option_c=question.option_c,
                option_d=question.option_d
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
            QuerySet of Question objects
        """
        from home.models import Question

        # Check if user has completed any lessons
        completed_lesson_ids = LessonProgress.objects.filter(
            user=user,
            is_completed=True
        ).distinct().values_list('lesson_id', flat=True)

        if completed_lesson_ids:
            # User has completed lessons - pull from those only
            question_pool = Question.objects.filter(
                lesson_id__in=completed_lesson_ids
            )
        else:
            # User hasn't completed any lessons - pull from all published lessons
            question_pool = Question.objects.filter(
                lesson__is_published=True
            )

        return question_pool

    @staticmethod
    def calculate_quest_score(quest, submitted_answers):
        """
        Calculate score for a quest submission.

        Args:
            quest: DailyQuest instance
            submitted_answers: dict mapping question IDs to submitted answers

        Returns:
            tuple: (correct_count, total_questions, xp_earned)
        """
        questions = DailyQuestQuestion.objects.filter(quest=quest)
        total_questions = questions.count()
        correct_count = 0

        for question in questions:
            submitted = submitted_answers.get(str(question.id), '').strip().lower()
            correct = question.correct_answer.strip().lower()

            if submitted == correct:
                correct_count += 1

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
            total_correct=Sum('score')
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
            total_correct=Sum('score')
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
