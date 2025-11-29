"""
Management command to ensure shapes and colors lessons are set to difficulty_level=1.

These lessons should always be treated as level 1 lessons.
"""

from django.core.management.base import BaseCommand

from home.models import Lesson


class Command(BaseCommand):
    help = 'Set shapes and colors lessons to difficulty_level=1'

    def handle(self, *args, **options):
        """Update shapes and colors lessons to level 1 for all languages."""
        updated_count = 0
        checked_count = 0
        
        # Find all shapes and colors lessons across all languages
        # Shapes/colors can have slugs like 'shapes', 'shapes-french', 'shapes-german', etc.
        from django.db.models import Q
        
        shapes_lessons = Lesson.objects.filter(
            Q(slug='shapes') | Q(slug__startswith='shapes-'),
            is_published=True
        )
        colors_lessons = Lesson.objects.filter(
            Q(slug='colors') | Q(slug__startswith='colors-'),
            is_published=True
        )
        
        self.stdout.write('Checking shapes lessons...')
        for lesson in shapes_lessons:
            checked_count += 1
            if lesson.difficulty_level != 1:
                lesson.difficulty_level = 1
                lesson.save(update_fields=['difficulty_level'])
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Updated {lesson.title} ({lesson.language}) to level 1'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ {lesson.title} ({lesson.language}) already at level 1'
                    )
                )
        
        self.stdout.write('\nChecking colors lessons...')
        for lesson in colors_lessons:
            checked_count += 1
            if lesson.difficulty_level != 1:
                lesson.difficulty_level = 1
                lesson.save(update_fields=['difficulty_level'])
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Updated {lesson.title} ({lesson.language}) to level 1'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ {lesson.title} ({lesson.language}) already at level 1'
                    )
                )
        
        self.stdout.write('\n' + '='*60)
        if updated_count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ All {checked_count} shapes and colors lessons are already at level 1'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Updated {updated_count} out of {checked_count} lesson(s) to level 1'
                )
            )
        
        # Show summary by language
        all_lessons = list(shapes_lessons) + list(colors_lessons)
        languages = sorted(set(lesson.language for lesson in all_lessons))
        self.stdout.write(f'\nLanguages with shapes/colors lessons: {", ".join(languages)}')

