"""
Django management command to create the Shapes lesson with flashcards and quiz questions.
"""
from django.core.management.base import BaseCommand
from home.models import Lesson, Flashcard, LessonQuizQuestion


class Command(BaseCommand):
    """Creates the Shapes lesson with flashcards and quiz questions."""
    help = 'Creates the Shapes lesson with flashcards and quiz'

    def handle(self, *args, **kwargs):
        """Create Shapes lesson with flashcards and quiz questions."""
        # Create or get the lesson
        lesson, created = Lesson.objects.get_or_create(
            title='Shapes in Spanish',
            defaults={
                'description': 'Learn basic shape names in Spanish',
                'language': 'Spanish',
                'difficulty_level': 'A1',
                'slug': 'shapes',
                'order': 1,
                'is_published': True,
            }
        )

        # IMPORTANT: Always update slug even if lesson exists (fixes production bug)
        if not created and lesson.slug != 'shapes':
            lesson.slug = 'shapes'
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

        # Create flashcards
        flashcards_data = [
            {'front': 'Circle', 'back': 'Círculo', 'order': 1},
            {'front': 'Square', 'back': 'Cuadrado', 'order': 2},
            {'front': 'Triangle', 'back': 'Triángulo', 'order': 3},
            {'front': 'Rectangle', 'back': 'Rectángulo', 'order': 4},
            {'front': 'Oval', 'back': 'Óvalo', 'order': 5},
            {'front': 'Star', 'back': 'Estrella', 'order': 6},
            {'front': 'Heart', 'back': 'Corazón', 'order': 7},
            {'front': 'Diamond', 'back': 'Diamante', 'order': 8},
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
                'question': 'What is "Circle" in Spanish?',
                'options': ['Cuadrado', 'Círculo', 'Triángulo', 'Rectángulo'],
                'correct_index': 1,
                'order': 1,
            },
            {
                'question': 'What is "Square" in Spanish?',
                'options': ['Estrella', 'Óvalo', 'Cuadrado', 'Corazón'],
                'correct_index': 2,
                'order': 2,
            },
            {
                'question': 'What is "Triangle" in Spanish?',
                'options': ['Triángulo', 'Círculo', 'Diamante', 'Rectángulo'],
                'correct_index': 0,
                'order': 3,
            },
            {
                'question': 'What is "Rectangle" in Spanish?',
                'options': ['Cuadrado', 'Óvalo', 'Triángulo', 'Rectángulo'],
                'correct_index': 3,
                'order': 4,
            },
            {
                'question': 'What is "Star" in Spanish?',
                'options': ['Estrella', 'Corazón', 'Diamante', 'Óvalo'],
                'correct_index': 0,
                'order': 5,
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

        self.stdout.write(self.style.SUCCESS('\nShapes lesson created successfully!'))
        self.stdout.write(f'Visit https://www.languagelearningplatform.org/lessons/{lesson.id}/ to view the lesson')
