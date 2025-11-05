# Generated data migration to fix shapes lesson slug
from django.db import migrations


def fix_shapes_lesson_slug(apps, schema_editor):
    """Add slug to shapes lesson if missing"""
    Lesson = apps.get_model('home', 'Lesson')
    
    # Update shapes lesson to have slug if it's missing
    shapes_lessons = Lesson.objects.filter(title='Shapes in Spanish', slug__isnull=True)
    for lesson in shapes_lessons:
        lesson.slug = 'shapes'
        lesson.save()
    
    # Also update any that might have null slug
    shapes_lessons_empty = Lesson.objects.filter(title='Shapes in Spanish', slug='')
    for lesson in shapes_lessons_empty:
        lesson.slug = 'shapes'
        lesson.save()


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0005_lesson_slug'),
    ]

    operations = [
        migrations.RunPython(fix_shapes_lesson_slug, migrations.RunPython.noop),
    ]

