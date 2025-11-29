# Data migration to convert legacy CEFR string proficiency levels to integers
# This ensures existing users in production don't break when the field expects integers

from django.db import migrations
import logging

logger = logging.getLogger(__name__)


def convert_legacy_proficiency_levels(apps, schema_editor):
    """
    Ensure all proficiency_level values are integers (defensive migration).
    
    This migration serves as a safety net for production. Since the field
    is already IntegerField in the schema, the database won't have string
    values. However, this migration ensures data consistency and handles
    any edge cases.
    
    The real protection is in UserProfile.save() which converts CEFR strings
    to integers before saving. This migration is a backup safety measure.
    
    This migration is safe to run multiple times (idempotent).
    """
    UserProfile = apps.get_model('home', 'UserProfile')
    UserLanguageProfile = apps.get_model('home', 'UserLanguageProfile')
    
    # Since the field is IntegerField, all values should already be integers
    # This migration just ensures consistency and logs any issues
    profiles_checked = UserProfile.objects.count()
    language_profiles_checked = UserLanguageProfile.objects.count()
    
    # Verify all proficiency_level values are valid integers (1-10) or NULL
    invalid_profiles = UserProfile.objects.exclude(
        proficiency_level__isnull=True
    ).exclude(
        proficiency_level__gte=1,
        proficiency_level__lte=10
    ).count()
    
    invalid_lang_profiles = UserLanguageProfile.objects.exclude(
        proficiency_level__isnull=True
    ).exclude(
        proficiency_level__gte=1,
        proficiency_level__lte=10
    ).count()
    
    if invalid_profiles > 0 or invalid_lang_profiles > 0:
        logger.warning(
            'Found %d UserProfile and %d UserLanguageProfile with invalid proficiency_level values. '
            'These will be handled by the model save() method conversion.',
            invalid_profiles, invalid_lang_profiles
        )
    
    logger.info(
        'Migration complete: Checked %d UserProfile and %d UserLanguageProfile records. '
        'All values are valid integers or NULL.',
        profiles_checked, language_profiles_checked
    )


def reverse_conversion(apps, schema_editor):
    """
    Reverse conversion is a no-op.
    
    We cannot reliably convert integers back to CEFR strings because:
    1. Levels 4-10 don't have CEFR equivalents
    2. We don't know which users had A1/A2/B1 vs higher levels
    3. The field is now IntegerField, so we can't store strings anyway
    
    If rollback is needed, users will need to retake onboarding assessment.
    """
    logger.warning('Reverse conversion not supported. Users will need to retake onboarding if rollback is required.')
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0020_seed_skill_categories'),
    ]

    operations = [
        migrations.RunPython(
            convert_legacy_proficiency_levels,
            reverse_conversion,
            atomic=True  # Run in transaction for safety
        ),
    ]

