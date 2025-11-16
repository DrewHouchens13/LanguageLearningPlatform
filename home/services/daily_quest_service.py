"""
Service for the modernized daily challenge experience.

This module replaces the legacy quiz-style daily quest with an interaction-
focused challenge. Users now complete the challenge by either onboarding into
an additional language or by finishing a lesson in the language they are
currently studying.
"""

import hashlib
import logging
from datetime import timedelta
from typing import Dict, List, Optional

from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from django.db.utils import OperationalError

from home.language_registry import (
    DEFAULT_LANGUAGE,
    get_language_metadata,
    get_supported_languages,
    normalize_language_name,
)
from home.models import DailyChallengeLog, UserLanguageProfile, UserProfile

logger = logging.getLogger(__name__)


class DailyQuestService:
    """Business logic for the revamped daily challenge."""

    XP_REWARD = 75

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @staticmethod
    def get_today_challenge(user) -> Dict[str, Optional[object]]:
        """Return the challenge card data for the authenticated user."""
        today = timezone.localdate()
        log = None
        try:
            log = DailyChallengeLog.objects.filter(user=user, date=today).first()
        except OperationalError:
            logger.warning(
                'DailyChallengeLog table missing while loading challenge for %s. '
                'Did you run migrations?',
                user.username
            )

        pending_languages = DailyQuestService._get_pending_languages(user)
        target_language = DailyQuestService._get_target_language(user)

        onboarding_action = None
        if pending_languages:
            selected_language = DailyQuestService._deterministic_choice(
                pending_languages,
                f"{today.isoformat()}:{user.id}:language"
            )
            onboarding_action = DailyQuestService._build_onboarding_action(selected_language)

        lesson_action = DailyQuestService._build_lesson_action(target_language)

        candidates = [('lesson', lesson_action)]
        if onboarding_action:
            candidates.append(('onboarding', onboarding_action))

        challenge_type, primary_action = DailyQuestService._deterministic_choice(
            candidates,
            f"{today.isoformat()}:{user.id}:mode"
        )

        return {
            'date': today,
            'completed': bool(log),
            'completed_via': log.completed_via if log else None,
            'xp_reward': DailyQuestService.XP_REWARD,
            'challenge_type': challenge_type,
            'pending_languages': pending_languages,
            'target_language': target_language,
            'primary_action': primary_action,
            'secondary_action': None,
            'log': log,
        }

    @staticmethod
    def handle_lesson_completion(user, language: str, lesson_title: Optional[str] = None):
        """Record challenge completion when a lesson is finished."""
        if not user.is_authenticated:
            return None

        normalized = normalize_language_name(language)
        metadata = {'lesson_title': lesson_title} if lesson_title else {}
        return DailyQuestService._mark_completed(user, 'lesson', normalized, metadata)

    @staticmethod
    def handle_onboarding_completion(user, language: str):
        """Record challenge completion when onboarding finishes for a language."""
        if not user.is_authenticated:
            return None

        normalized = normalize_language_name(language)
        metadata = {'onboarding_language': normalized}
        return DailyQuestService._mark_completed(user, 'onboarding', normalized, metadata)

    @staticmethod
    def get_weekly_stats(user) -> Dict[str, int]:
        """Aggregate challenge stats for the trailing 7-day window."""
        week_ago = timezone.localdate() - timedelta(days=7)
        try:
            logs = DailyChallengeLog.objects.filter(user=user, date__gte=week_ago)
            return DailyQuestService._compile_stats(logs)
        except OperationalError:
            logger.warning(
                'DailyChallengeLog table missing while loading weekly stats for %s',
                user.username
            )
            return DailyQuestService._empty_stats()

    @staticmethod
    def get_lifetime_stats(user) -> Dict[str, int]:
        """Aggregate historical challenge stats for dashboards."""
        try:
            logs = DailyChallengeLog.objects.filter(user=user)
            return DailyQuestService._compile_stats(logs)
        except OperationalError:
            logger.warning(
                'DailyChallengeLog table missing while loading lifetime stats for %s',
                user.username
            )
            return DailyQuestService._empty_stats()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _compile_stats(queryset):
        total_xp = queryset.aggregate(total=Sum('xp_awarded'))['total'] or 0
        lesson_count = queryset.filter(completed_via='lesson').count()
        onboarding_count = queryset.filter(completed_via='onboarding').count()
        return {
            'challenges_completed': queryset.count(),
            'xp_earned': total_xp,
            'lesson_completions': lesson_count,
            'onboarding_completions': onboarding_count,
        }

    @staticmethod
    def _empty_stats():
        return {
            'challenges_completed': 0,
            'xp_earned': 0,
            'lesson_completions': 0,
            'onboarding_completions': 0,
        }

    @staticmethod
    def _build_onboarding_action(language: Dict[str, str]) -> Optional[Dict[str, str]]:
        if not language:
            return None

        slug = language['slug']
        english_name = language['name']
        return {
            'type': 'onboarding',
            'language': english_name,
            'native_name': language['native_name'],
            'flag': language['flag'],
            'label': f"Complete onboarding for {english_name}",
            'description': 'Take the 10-question placement to unlock new lessons.',
            'cta_label': f"Start {english_name} onboarding",
            'cta_url': f"{reverse('onboarding_welcome')}?language={slug}",
            'icon': '🚀',
        }

    @staticmethod
    def _build_lesson_action(target_language: str) -> Dict[str, str]:
        metadata = get_language_metadata(target_language)
        slug = target_language.lower()
        return {
            'type': 'lesson',
            'language': target_language,
            'native_name': metadata['native_name'],
            'flag': metadata['flag'],
            'label': f"Complete a {metadata['native_name']} lesson",
            'description': 'Finish any lesson in your current language to earn bonus XP.',
            'cta_label': 'Browse lessons',
            'cta_url': reverse('lessons_by_language', args=[slug]),
            'icon': '📘',
        }

    @staticmethod
    def _deterministic_choice(options, key):
        if not options:
            return None
        digest = hashlib.sha256(key.encode('utf-8')).digest()
        index = int.from_bytes(digest[:8], byteorder='big') % len(options)
        return options[index]

    @staticmethod
    def _mark_completed(user, completed_via: str, language: str, metadata: Optional[Dict[str, str]] = None):
        today = timezone.localdate()
        metadata = metadata or {}

        try:
            log, created = DailyChallengeLog.objects.get_or_create(
                user=user,
                date=today,
                defaults={
                    'completed_via': completed_via,
                    'language': language,
                    'metadata': metadata,
                }
            )
        except OperationalError:
            logger.warning(
                'DailyChallengeLog table missing while marking %s completion for %s',
                completed_via,
                user.username
            )
            return {
                'completed': False,
                'error': 'missing_table',
            }

        if not created:
            return {
                'already_completed': True,
                'completed_via': log.completed_via,
                'language': log.language,
                'xp_awarded': log.xp_awarded,
            }

        profile = DailyQuestService._ensure_profile(user)
        xp_awarded = DailyQuestService.XP_REWARD

        try:
            xp_result = profile.award_xp(xp_awarded)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error('Failed to award XP for daily challenge: %s', exc)
            xp_result = None

        log.completed_via = completed_via
        log.language = language
        log.metadata = metadata
        log.xp_awarded = xp_awarded
        log.save(update_fields=['completed_via', 'language', 'metadata', 'xp_awarded', 'updated_at'])

        return {
            'completed': True,
            'completed_via': completed_via,
            'language': language,
            'xp_awarded': xp_awarded,
            'xp_result': xp_result,
            'log_id': log.id,
        }

    @staticmethod
    def _get_pending_languages(user) -> List[Dict[str, str]]:
        completed = set(
            normalize_language_name(lang)
            for lang in UserLanguageProfile.objects.filter(
                user=user,
                has_completed_onboarding=True
            ).values_list('language', flat=True)
        )

        pending = []
        for entry in get_supported_languages(include_flags=True):
            normalized = normalize_language_name(entry['name'])
            if normalized not in completed:
                pending.append({
                    **entry,
                    'name': normalized,
                })
        return pending

    @staticmethod
    def _get_target_language(user) -> str:
        profile = DailyQuestService._ensure_profile(user)
        return normalize_language_name(profile.target_language or DEFAULT_LANGUAGE)

    @staticmethod
    def _ensure_profile(user) -> UserProfile:
        try:
            return user.profile
        except UserProfile.DoesNotExist:
            return UserProfile.objects.create(user=user)
