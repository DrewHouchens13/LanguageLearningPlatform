from django.db import migrations


LANGUAGES_TO_SEED = ['French', 'German', 'Korean']


def seed_multilanguage_content(apps, schema_editor):
    Lesson = apps.get_model('home', 'Lesson')
    Flashcard = apps.get_model('home', 'Flashcard')
    LessonQuizQuestion = apps.get_model('home', 'LessonQuizQuestion')
    OnboardingQuestion = apps.get_model('home', 'OnboardingQuestion')

    from home.seed_content import ONBOARDING_QUESTION_SETS, build_lesson_blueprints

    for language in LANGUAGES_TO_SEED:
        question_set = ONBOARDING_QUESTION_SETS.get(language, [])
        for question in question_set:
            OnboardingQuestion.objects.update_or_create(
                language=language,
                question_number=question['question_number'],
                defaults={
                    'question_text': question['question_text'],
                    'difficulty_level': question['difficulty_level'],
                    'option_a': question['option_a'],
                    'option_b': question['option_b'],
                    'option_c': question['option_c'],
                    'option_d': question['option_d'],
                    'correct_answer': question['correct_answer'],
                    'explanation': question['explanation'],
                    'difficulty_points': question['difficulty_points'],
                }
            )

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


def remove_multilanguage_content(apps, schema_editor):
    Lesson = apps.get_model('home', 'Lesson')
    Flashcard = apps.get_model('home', 'Flashcard')
    LessonQuizQuestion = apps.get_model('home', 'LessonQuizQuestion')
    OnboardingQuestion = apps.get_model('home', 'OnboardingQuestion')

    from home.seed_content import LESSON_CARD_DATA

    slugs_to_remove = []
    for language in LANGUAGES_TO_SEED:
        slugs_to_remove.extend([
            f"{config['slug']}-{language.lower()}"
            for config in LESSON_CARD_DATA.values()
        ])

    lessons = list(Lesson.objects.filter(slug__in=slugs_to_remove))
    for lesson in lessons:
        Flashcard.objects.filter(lesson=lesson).delete()
        LessonQuizQuestion.objects.filter(lesson=lesson).delete()
    Lesson.objects.filter(id__in=[lesson.id for lesson in lessons]).delete()

    OnboardingQuestion.objects.filter(language__in=LANGUAGES_TO_SEED).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0013_lessoncompletion_language_quizresult_language_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_multilanguage_content, remove_multilanguage_content),
    ]

