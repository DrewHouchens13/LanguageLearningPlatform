"""
Quiz-style daily challenge service.

Generates five-question multiple choice quizzes per user language each day,
tracks attempts, and awards XP proportional to performance.
"""

from __future__ import annotations

import logging
import secrets
from datetime import timedelta
from typing import Dict, List, Optional, Sequence, Tuple

from django.db import IntegrityError, transaction
from django.db.models import Count, Sum
from django.utils import timezone

from home.language_registry import (
    DEFAULT_LANGUAGE,
    get_language_metadata,
    normalize_language_name,
)
from home.models import (
    DailyQuest,
    DailyQuestQuestion,
    Lesson,
    LessonAttempt,
    UserDailyQuestAttempt,
    UserProfile,
)

logger = logging.getLogger(__name__)
_random = secrets.SystemRandom()


class DailyQuestService:
    """Business logic for the five-question daily challenge."""

    QUESTIONS_PER_CHALLENGE = 5
    MIN_OPTIONS = 4
    XP_RATIO = 0.75  # 75% of lesson XP
    MIN_REWARD = 25  # floor so easier lessons still feel meaningful

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @staticmethod
    def get_today_challenge(user) -> Optional[Dict[str, object]]:
        """
        Return today's challenge metadata (quest + attempt) for the user.

        Returns None if no eligible lessons exist for the user's language.
        """
        if not user.is_authenticated:
            return None

        try:
            quest = DailyQuestService._ensure_daily_quest(user)
        except ValueError as exc:
            logger.info('Daily quest unavailable for %s: %s', user.username, exc)
            return None

        attempt = DailyQuestService._get_attempt(user, quest)
        metadata = get_language_metadata(quest.language)

        return {
            'quest': quest,
            'attempt': attempt,
            'questions': quest.questions.all(),
            'language_metadata': metadata,
            'is_completed': bool(attempt and attempt.is_completed),
            'xp_reward': quest.xp_reward,
        }

    @staticmethod
    def submit_challenge(user, post_data) -> Dict[str, object]:
        """
        Grade and record the user's submission for today's quest.
        """
        quest = DailyQuestService._ensure_daily_quest(user)
        attempt = DailyQuestService._get_or_create_attempt(user, quest)

        if attempt.is_completed:
            return {
                'already_completed': True,
                'correct': attempt.correct_answers,
                'total': attempt.total_questions,
                'xp_awarded': attempt.xp_earned,
            }

        correct, total = DailyQuestService.calculate_quest_score(quest, post_data)
        attempt.correct_answers = correct
        attempt.total_questions = total
        attempt.xp_earned = attempt.calculate_xp()
        attempt.is_completed = True
        attempt.completed_at = timezone.now()
        attempt.save(update_fields=[
            'correct_answers',
            'total_questions',
            'xp_earned',
            'is_completed',
            'completed_at',
        ])

        xp_result = DailyQuestService._award_profile_xp(user, attempt.xp_earned)

        return {
            'correct': correct,
            'total': total,
            'xp_awarded': attempt.xp_earned,
            'xp_result': xp_result,
        }

    @staticmethod
    def get_weekly_stats(user) -> Dict[str, float]:
        """
        Aggregate stats for challenges completed within the past 7 days.
        """
        seven_days_ago = timezone.now() - timedelta(days=7)
        attempts = UserDailyQuestAttempt.objects.filter(
            user=user,
            is_completed=True,
            completed_at__gte=seven_days_ago,
        )
        return DailyQuestService._compile_stats(attempts)

    @staticmethod
    def get_lifetime_stats(user) -> Dict[str, float]:
        """
        Aggregate stats across all historical challenges for dashboards.
        """
        attempts = UserDailyQuestAttempt.objects.filter(
            user=user,
            is_completed=True,
        )
        return DailyQuestService._compile_stats(attempts)

    @staticmethod
    def calculate_quest_score(quest: DailyQuest, answers: Dict[str, str]) -> Tuple[int, int]:
        """
        Count how many answers are correct for the given quest submission.
        """
        correct = 0
        total = quest.questions.count()

        for question in quest.questions.all():
            raw_value = answers.get(f'question_{question.id}')
            try:
                selected_index = int(raw_value)
            except (TypeError, ValueError):
                continue

            if selected_index == question.correct_index:
                correct += 1

        return correct, total

    # ------------------------------------------------------------------
    # Quest generation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _ensure_daily_quest(user) -> DailyQuest:
        """Fetch or create today's quest for the user's active language."""
        today = timezone.localdate()
        language = DailyQuestService._get_user_language(user)

        quest = DailyQuest.objects.filter(date=today, language=language).first()
        if quest:
            return quest

        return DailyQuestService._create_daily_quest(language, today, user)

    @staticmethod
    def _create_daily_quest(language: str, quest_date, user) -> DailyQuest:
        """Create a new quest and snapshot its questions."""
        lesson = DailyQuestService._select_random_lesson(language, user)
        if lesson is None:
            raise ValueError(f"No lessons available for {language}")

        xp_reward = DailyQuestService._calculate_reward(lesson)
        description = f"Answer 5 questions pulled from {lesson.title}."

        try:
            with transaction.atomic():
                quest = DailyQuest.objects.create(
                    date=quest_date,
                    title=f"Daily {lesson.language} Challenge",
                    description=description,
                    language=language,
                    based_on_lesson=lesson,
                    quest_type='quiz',
                    xp_reward=xp_reward,
                )
                DailyQuestService._generate_questions(quest, lesson)
                return quest
        except IntegrityError:
            # Another request created it concurrently; fetch the existing row.
            logger.info('Quest already existed for %s on %s', language, quest_date)
            return DailyQuest.objects.get(date=quest_date, language=language)

    @staticmethod
    def _select_random_lesson(language: str, user) -> Optional[Lesson]:
        """
        Prefer lessons the user has completed, fallback to any published lesson.
        """
        lessons = Lesson.objects.filter(
            language=language,
            is_published=True,
        ).annotate(
            quiz_count=Count('quiz_questions'),
            card_count=Count('cards'),
        )

        def has_enough_content(entry: Lesson) -> bool:
            return max(entry.quiz_count, entry.card_count) >= DailyQuestService.QUESTIONS_PER_CHALLENGE

        eligible = [lesson for lesson in lessons if has_enough_content(lesson)]
        if not eligible:
            return None

        completed_ids = DailyQuestService._get_completed_lesson_ids(user, language)
        prioritized = [lesson for lesson in eligible if lesson.id in completed_ids]
        pool = prioritized or eligible
        return _random.choice(pool)

    @staticmethod
    def _generate_questions(quest: DailyQuest, lesson: Lesson) -> None:
        """Snapshot 5 questions (multiple choice) into DailyQuestQuestion."""
        bank = DailyQuestService._build_question_bank(lesson)
        if len(bank) < DailyQuestService.QUESTIONS_PER_CHALLENGE:
            raise ValueError("Not enough questions to build the challenge.")

        selected = _random.sample(bank, DailyQuestService.QUESTIONS_PER_CHALLENGE)
        DailyQuestQuestion.objects.bulk_create([
            DailyQuestQuestion(
                daily_quest=quest,
                question_text=item['question'],
                answer_text=item['answer'],
                options=item['options'],
                correct_index=item['correct_index'],
                order=index,
                difficulty_level='medium',
            )
            for index, item in enumerate(selected, start=1)
        ])

    @staticmethod
    def _build_question_bank(lesson: Lesson) -> List[Dict[str, object]]:
        """Return a reusable bank of MC questions for the lesson."""
        quiz_questions = list(lesson.quiz_questions.all())
        bank: List[Dict[str, object]] = []

        if len(quiz_questions) >= DailyQuestService.QUESTIONS_PER_CHALLENGE:
            for question in quiz_questions:
                options = list(question.options or [])
                if len(options) < DailyQuestService.MIN_OPTIONS:
                    continue
                bank.append({
                    'question': question.question,
                    'options': options,
                    'correct_index': question.correct_index,
                    'answer': options[question.correct_index],
                })
        else:
            cards = list(lesson.cards.all())
            for card in cards:
                distractors = [c.back_text for c in cards if c.id != card.id]
                if len(distractors) < DailyQuestService.MIN_OPTIONS - 1:
                    continue
                options = DailyQuestService._build_options(card.back_text, distractors)
                bank.append({
                    'question': f'What is "{card.front_text}" in {lesson.language}?',
                    'options': options,
                    'correct_index': options.index(card.back_text),
                    'answer': card.back_text,
                })

        return bank

    @staticmethod
    def _build_options(correct_answer: str, distractors: Sequence[str]) -> List[str]:
        """Build a shuffled list of options with the correct answer included."""
        sample = list(_random.sample(list(distractors), DailyQuestService.MIN_OPTIONS - 1))
        sample.append(correct_answer)
        _random.shuffle(sample)
        return sample

    @staticmethod
    def _calculate_reward(lesson: Lesson) -> int:
        reward = int(max(DailyQuestService.MIN_REWARD, lesson.xp_value * DailyQuestService.XP_RATIO))
        return reward or DailyQuestService.MIN_REWARD

    # ------------------------------------------------------------------
    # Attempt helpers / stats
    # ------------------------------------------------------------------
    @staticmethod
    def _get_attempt(user, quest: DailyQuest) -> Optional[UserDailyQuestAttempt]:
        return UserDailyQuestAttempt.objects.filter(user=user, daily_quest=quest).first()

    @staticmethod
    def _get_or_create_attempt(user, quest: DailyQuest) -> UserDailyQuestAttempt:
        attempt, _ = UserDailyQuestAttempt.objects.get_or_create(
            user=user,
            daily_quest=quest,
            defaults={'total_questions': DailyQuestService.QUESTIONS_PER_CHALLENGE},
        )
        return attempt

    @staticmethod
    def _get_completed_lesson_ids(user, language: str) -> set:
        attempts = LessonAttempt.objects.filter(
            user=user,
            lesson__language=language,
        ).values_list('lesson_id', flat=True)
        return set(attempts)

    @staticmethod
    def _get_user_language(user) -> str:
        profile = DailyQuestService._ensure_profile(user)
        today = timezone.localdate()
        if (
            profile.daily_challenge_language
            and profile.daily_challenge_language_date == today
        ):
            return profile.daily_challenge_language

        locked_language = normalize_language_name(profile.target_language or DEFAULT_LANGUAGE)
        profile.daily_challenge_language = locked_language
        profile.daily_challenge_language_date = today
        profile.save(update_fields=['daily_challenge_language', 'daily_challenge_language_date'])
        return locked_language

    @staticmethod
    def _ensure_profile(user) -> UserProfile:
        try:
            return user.profile
        except UserProfile.DoesNotExist:
            return UserProfile.objects.create(user=user)

    @staticmethod
    def _award_profile_xp(user, xp_awarded: int):
        if xp_awarded <= 0:
            return None

        profile = DailyQuestService._ensure_profile(user)
        try:
            return profile.award_xp(xp_awarded)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error('Failed to award XP for daily challenge: %s', exc, exc_info=True)
            return None

    @staticmethod
    def _compile_stats(queryset) -> Dict[str, float]:
        aggregates = queryset.aggregate(
            correct=Sum('correct_answers'),
            total=Sum('total_questions'),
            xp=Sum('xp_earned'),
            count=Count('id'),
        )
        accuracy = DailyQuestService._calculate_accuracy(
            aggregates.get('correct') or 0,
            aggregates.get('total') or 0,
        )
        return {
            'challenges_completed': aggregates.get('count') or 0,
            'xp_earned': aggregates.get('xp') or 0,
            'accuracy': accuracy,
        }

    @staticmethod
    def _calculate_accuracy(correct: int, total: int) -> float:
        if not total:
            return 0.0
        return round((correct / total) * 100, 1)
