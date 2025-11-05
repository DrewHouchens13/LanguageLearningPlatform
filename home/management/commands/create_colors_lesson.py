from django.core.management.base import BaseCommand
from home.models import Lesson, Flashcard, LessonQuizQuestion


class Command(BaseCommand):
    help = 'Creates the Colors lesson with flashcards and quiz'

    def handle(self, *args, **kwargs):
        # Create or get the lesson
        lesson, created = Lesson.objects.get_or_create(
            title='Colors in Spanish',
            defaults={
                'description': 'Learn basic color names in Spanish with interactive flashcards',
                'language': 'Spanish',
                'difficulty_level': 'A1',
                'slug': 'colors',
                'order': 2,  # After shapes lesson
                'is_published': True,
            }
        )

        # IMPORTANT: Always update slug even if lesson exists (fixes production bug)
        if not created and lesson.slug != 'colors':
            lesson.slug = 'colors'
            lesson.save()
            self.stdout.write(self.style.WARNING(f'Fixed missing slug for existing lesson: {lesson.title}'))

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created lesson: {lesson.title}'))
        else:
            self.stdout.write(self.style.WARNING(f'Lesson already exists: {lesson.title}'))
            # Clear existing data to recreate
            lesson.cards.all().delete()
            lesson.quiz_questions.all().delete()
            self.stdout.write('Cleared existing flashcards and questions')

        # Create flashcards with color data
        flashcards_data = [
            {'front': 'Red', 'back': 'Rojo', 'order': 1},
            {'front': 'Blue', 'back': 'Azul', 'order': 2},
            {'front': 'Yellow', 'back': 'Amarillo', 'order': 3},
            {'front': 'Green', 'back': 'Verde', 'order': 4},
            {'front': 'Purple', 'back': 'Morado', 'order': 5},
            {'front': 'Orange', 'back': 'Naranja', 'order': 6},
            {'front': 'Pink', 'back': 'Rosa', 'order': 7},
            {'front': 'Brown', 'back': 'Marrón', 'order': 8},
            {'front': 'Black', 'back': 'Negro', 'order': 9},
            {'front': 'White', 'back': 'Blanco', 'order': 10},
        ]

        # Use bulk_create for better performance
        flashcards = [
            Flashcard(
                lesson=lesson,
                front_text=card_data['front'],
                back_text=card_data['back'],
                order=card_data['order'],
            )
            for card_data in flashcards_data
        ]
        Flashcard.objects.bulk_create(flashcards)
        self.stdout.write(f'  Created {len(flashcards)} flashcards')

        # Create quiz questions
        quiz_questions = [
            {
                'question': 'What is "Red" in Spanish?',
                'options': ['Azul', 'Rojo', 'Verde', 'Amarillo'],
                'correct_index': 1,
                'order': 1,
            },
            {
                'question': 'What is "Blue" in Spanish?',
                'options': ['Rojo', 'Azul', 'Verde', 'Amarillo'],
                'correct_index': 1,
                'order': 2,
            },
            {
                'question': '"Verde" means...',
                'options': ['Purple', 'Green', 'Orange', 'Pink'],
                'correct_index': 1,
                'order': 3,
            },
            {
                'question': 'What color is "Amarillo"?',
                'options': ['Purple', 'Yellow', 'Orange', 'Pink'],
                'correct_index': 1,
                'order': 4,
            },
            {
                'question': 'What is "Black" in Spanish?',
                'options': ['Blanco', 'Negro', 'Marrón', 'Gris'],
                'correct_index': 1,
                'order': 5,
            },
            {
                'question': 'What is "Pink" in Spanish?',
                'options': ['Rosa', 'Rojo', 'Morado', 'Naranja'],
                'correct_index': 0,
                'order': 6,
            },
            {
                'question': '"Morado" means...',
                'options': ['Purple', 'Brown', 'Orange', 'White'],
                'correct_index': 0,
                'order': 7,
            },
            {
                'question': 'Which word means both "orange" (the color) and "orange" (the fruit) in Spanish?',
                'options': ['Naranja', 'Anaranjado', 'Rosa', 'Rojo'],
                'correct_index': 0,
                'order': 8,
            },
        ]

        # Use bulk_create for better performance
        questions = [
            LessonQuizQuestion(
                lesson=lesson,
                question=q_data['question'],
                options=q_data['options'],
                correct_index=q_data['correct_index'],
                order=q_data['order'],
            )
            for q_data in quiz_questions
        ]
        LessonQuizQuestion.objects.bulk_create(questions)
        self.stdout.write(f'  Created {len(questions)} quiz questions')

        # Link shapes lesson to colors lesson for progression
        try:
            shapes_lesson = Lesson.objects.get(title='Shapes in Spanish')
            shapes_lesson.next_lesson = lesson
            shapes_lesson.save()
            self.stdout.write(f'  Linked Shapes lesson -> Colors lesson')
        except Lesson.DoesNotExist:
            self.stdout.write(self.style.WARNING('  Shapes lesson not found, skipping link'))

        self.stdout.write(self.style.SUCCESS('\nColors lesson created successfully!'))
        self.stdout.write(f'Visit https://www.languagelearningplatform.org/lessons/{lesson.id}/ to view the lesson')
