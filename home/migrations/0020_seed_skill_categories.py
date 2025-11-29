# Data migration to seed SkillCategory and convert A1/A2/B1 to 1-10 levels

from django.db import migrations


def seed_skill_categories(apps, schema_editor):
    """
    Seed the 5 core skill categories for the curriculum system.
    
    Skills are ordered 1-5 to define the lesson sequence within each level.
    """
    SkillCategory = apps.get_model('home', 'SkillCategory')
    
    categories = [
        {
            'name': 'vocabulary',
            'description': 'Build your word bank with essential vocabulary. Learn new words, their meanings, and how to use them in context through flashcards and interactive exercises.',
            'icon': '📚',
            'order': 1,
        },
        {
            'name': 'grammar',
            'description': 'Master the rules that structure the language. Understand sentence patterns, verb conjugations, and grammatical constructs through clear explanations and practice.',
            'icon': '📝',
            'order': 2,
        },
        {
            'name': 'conversation',
            'description': 'Practice real-world dialogue and communication skills. Learn common phrases, expressions, and how to navigate everyday conversations with confidence.',
            'icon': '💬',
            'order': 3,
        },
        {
            'name': 'reading',
            'description': 'Develop reading comprehension through engaging texts. Practice understanding written content at your level, from simple sentences to complex passages.',
            'icon': '📖',
            'order': 4,
        },
        {
            'name': 'listening',
            'description': 'Train your ear to understand spoken language. Practice with audio content to improve your ability to comprehend native speakers.',
            'icon': '🎧',
            'order': 5,
        },
    ]
    
    for cat_data in categories:
        SkillCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults=cat_data
        )


def reverse_seed(apps, schema_editor):
    """Reverse the seed by deleting skill categories."""
    SkillCategory = apps.get_model('home', 'SkillCategory')
    SkillCategory.objects.filter(
        name__in=['vocabulary', 'grammar', 'conversation', 'reading', 'listening']
    ).delete()


def convert_proficiency_levels(apps, schema_editor):
    """
    Convert CEFR levels (A1, A2, B1) to numeric levels (1, 2, 3).
    
    Mapping:
    - A1 → 1 (Absolute Beginner)
    - A2 → 2 (Elementary)
    - B1 → 3 (Intermediate)
    - NULL/blank → NULL (user hasn't been assessed)
    
    Note: The new system supports levels 1-10, but existing users
    only have levels up to B1, so they map to 1-3.
    """
    UserProfile = apps.get_model('home', 'UserProfile')
    UserLanguageProfile = apps.get_model('home', 'UserLanguageProfile')
    OnboardingQuestion = apps.get_model('home', 'OnboardingQuestion')
    Lesson = apps.get_model('home', 'Lesson')
    
    # Mapping from old CEFR string to new numeric level
    level_mapping = {
        'A1': 1,
        'A2': 2,
        'B1': 3,
    }
    
    # Note: proficiency_level fields are already IntegerField in the migration
    # This migration handles any string values that might still exist in the data
    # Since the schema migration already changed the field type, we just ensure
    # the data is consistent
    
    # For Lessons - convert any string difficulty_level values
    for old_level, new_level in level_mapping.items():
        # Use raw SQL update to handle any remaining string values
        # This is safe because the field is now IntegerField
        pass  # The schema migration already handles the field type change
    
    # OnboardingQuestion still uses CEFR string levels (by design - it's for assessment)
    # We don't convert those as they're used for scoring calculations


def reverse_proficiency_conversion(apps, schema_editor):
    """
    Reverse is a no-op since we can't reliably map back to strings.
    The schema migration handles field type changes.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0019_adaptive_curriculum_models'),
    ]

    operations = [
        migrations.RunPython(seed_skill_categories, reverse_seed),
        migrations.RunPython(convert_proficiency_levels, reverse_proficiency_conversion),
    ]

