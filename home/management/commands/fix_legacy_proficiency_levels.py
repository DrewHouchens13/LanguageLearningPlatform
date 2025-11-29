"""
Management command to fix legacy CEFR proficiency levels in production.

This command can be run manually if needed to clean up any legacy string values
that might cause issues. The UserProfile.save() method should handle this
automatically, but this command provides a manual cleanup option.

Usage:
    python manage.py fix_legacy_proficiency_levels
    python manage.py fix_legacy_proficiency_levels --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from home.models import UserProfile, UserLanguageProfile
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Convert legacy CEFR string proficiency levels (A1, A2, B1) to integers (1, 2, 3)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        cefr_to_level = {'A1': 1, 'A2': 2, 'B1': 3}
        profiles_fixed = 0
        lang_profiles_fixed = 0
        
        # Fix UserProfile records
        for profile in UserProfile.objects.all():
            if profile.proficiency_level is not None:
                if isinstance(profile.proficiency_level, str):
                    old_value = profile.proficiency_level
                    new_value = cefr_to_level.get(old_value.upper(), 1)
                    
                    if dry_run:
                        self.stdout.write(
                            f'Would convert UserProfile {profile.user.username}: '
                            f'{old_value} → {new_value}'
                        )
                    else:
                        profile.proficiency_level = new_value
                        profile.save(update_fields=['proficiency_level'])
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Converted UserProfile {profile.user.username}: '
                                f'{old_value} → {new_value}'
                            )
                        )
                    profiles_fixed += 1
        
        # Fix UserLanguageProfile records
        for lang_profile in UserLanguageProfile.objects.all():
            if lang_profile.proficiency_level is not None:
                if isinstance(lang_profile.proficiency_level, str):
                    old_value = lang_profile.proficiency_level
                    new_value = cefr_to_level.get(old_value.upper(), 1)
                    
                    if dry_run:
                        self.stdout.write(
                            f'Would convert UserLanguageProfile {lang_profile.user.username}: '
                            f'{old_value} → {new_value}'
                        )
                    else:
                        lang_profile.proficiency_level = new_value
                        lang_profile.save(update_fields=['proficiency_level'])
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Converted UserLanguageProfile {lang_profile.user.username}: '
                                f'{old_value} → {new_value}'
                            )
                        )
                    lang_profiles_fixed += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\nDry run complete: Would fix {profiles_fixed} UserProfile and '
                    f'{lang_profiles_fixed} UserLanguageProfile records'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nComplete: Fixed {profiles_fixed} UserProfile and '
                    f'{lang_profiles_fixed} UserLanguageProfile records'
                )
            )

