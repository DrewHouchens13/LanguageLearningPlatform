from django.db import migrations


def seed_lessons(apps, schema_editor):
    Lesson = apps.get_model('home', 'Lesson')
    Flashcard = apps.get_model('home', 'Flashcard')
    LessonQuizQuestion = apps.get_model('home', 'LessonQuizQuestion')

    from home.language_registry import LANGUAGE_METADATA
    from home.seed_content import build_lesson_blueprints

    for language in sorted(LANGUAGE_METADATA.keys()):
        if language == 'Spanish':
            continue  # Spanish lessons already exist from initial seed data
        lesson_map = {}
        for blueprint in build_lesson_blueprints(language):
            lesson, _ = Lesson.objects.update_or_create(
                slug=blueprint['slug'],
                defaults={
                    'title': blueprint['title'],
                    'description': blueprint['description'],
                    'language': blueprint['language'],
                    'order': blueprint['order'],
                    'category': blueprint['category'],
                    'lesson_type': blueprint['lesson_type'],
                    'xp_value': blueprint['xp_value'],
                    'is_published': True,
                }
            )
            lesson_map[blueprint['key']] = lesson

            Flashcard.objects.filter(lesson=lesson).delete()
            Flashcard.objects.bulk_create([
                Flashcard(
                    lesson=lesson,
                    front_text=card['front_text'],
                    back_text=card['back_text'],
                    image_url=card.get('image_url', ''),
                    order=card['order'],
                )
                for card in blueprint['flashcards']
            ])

            LessonQuizQuestion.objects.filter(lesson=lesson).delete()
            LessonQuizQuestion.objects.bulk_create([
                LessonQuizQuestion(
                    lesson=lesson,
                    question=q['question'],
                    options=q['options'],
                    correct_index=q['correct_index'],
                    order=q['order'],
                )
                for q in blueprint['quiz_questions']
            ])

        shapes = lesson_map.get('shapes')
        colors = lesson_map.get('colors')
        if shapes and colors:
            shapes.next_lesson = colors
            shapes.save(update_fields=['next_lesson'])


def remove_lessons(apps, schema_editor):
    Lesson = apps.get_model('home', 'Lesson')
    Flashcard = apps.get_model('home', 'Flashcard')
    LessonQuizQuestion = apps.get_model('home', 'LessonQuizQuestion')

    from home.language_registry import LANGUAGE_METADATA
    from home.seed_content import LESSON_CARD_DATA

    slugs = set()
    for language in LANGUAGE_METADATA.keys():
        for config in LESSON_CARD_DATA.values():
            if language.lower() == 'spanish':
                continue
            slugs.add(f"{config['slug']}-{language.lower()}")

    lessons = list(Lesson.objects.filter(slug__in=slugs))
    Flashcard.objects.filter(lesson__in=lessons).delete()
    LessonQuizQuestion.objects.filter(lesson__in=lessons).delete()
    Lesson.objects.filter(id__in=[lesson.id for lesson in lessons]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0015_dailychallengelog'),
    ]

    operations = [
        migrations.RunPython(seed_lessons, remove_lessons),
    ]

