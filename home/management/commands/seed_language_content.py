from django.core.management.base import BaseCommand, CommandError

from home.language_registry import normalize_language_name
from home.models import (Flashcard, Lesson, LessonQuizQuestion,
                         OnboardingQuestion)
from home.seed_content import ONBOARDING_QUESTION_SETS, build_lesson_blueprints


class Command(BaseCommand):
    """
    Seed onboarding questions and lesson content for one or more languages.

    Usage:
        python manage.py seed_language_content --languages French German
        python manage.py seed_language_content  # seeds every language in dataset
    """

    help = 'Create or update onboarding questions and lessons for target languages.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--languages',
            nargs='+',
            help='Language names to seed (default: all languages available in dataset)',
        )

    def handle(self, *args, **options):
        requested_languages = options.get('languages')
        if requested_languages:
            languages = [normalize_language_name(lang) for lang in requested_languages]
        else:
            languages = sorted(ONBOARDING_QUESTION_SETS.keys())

        if not languages:
            raise CommandError('No languages available to seed.')

        for language in languages:
            if language not in ONBOARDING_QUESTION_SETS:
                self.stdout.write(self.style.WARNING(f'Skipping {language}: no onboarding data available.'))
                continue

            self.stdout.write(self.style.MIGRATE_HEADING(f'Seeding {language} onboarding questions...'))
            self._seed_onboarding_questions(language)

            self.stdout.write(self.style.MIGRATE_HEADING(f'Seeding {language} lessons...'))
            self._seed_lessons(language)

        self.stdout.write(self.style.SUCCESS('Seeding complete.'))

    def _seed_onboarding_questions(self, language):
        for question in ONBOARDING_QUESTION_SETS[language]:
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

    def _seed_lessons(self, language):
        blueprints = build_lesson_blueprints(language)
        lesson_map = {}

        for blueprint in blueprints:
            # Shapes and colors should always be level 1
            difficulty_level = 1 if blueprint['slug'] in ['shapes', 'colors'] else 1
            
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
                    'difficulty_level': difficulty_level,
                    'is_published': True,
                }
            )
            lesson_map[blueprint['key']] = lesson

            lesson.cards.all().delete()
            flashcards = [
                Flashcard(
                    lesson=lesson,
                    front_text=card['front_text'],
                    back_text=card['back_text'],
                    image_url=card.get('image_url', ''),
                    order=card['order'],
                )
                for card in blueprint['flashcards']
            ]
            Flashcard.objects.bulk_create(flashcards)

            lesson.quiz_questions.all().delete()
            questions = [
                LessonQuizQuestion(
                    lesson=lesson,
                    question=q['question'],
                    options=q['options'],
                    correct_index=q['correct_index'],
                    order=q['order'],
                )
                for q in blueprint['quiz_questions']
            ]
            LessonQuizQuestion.objects.bulk_create(questions)

        # Link shapes -> colors progression if both exist
        shapes = lesson_map.get('shapes')
        colors = lesson_map.get('colors')
        if shapes and colors:
            shapes.next_lesson = colors
            shapes.save(update_fields=['next_lesson'])

