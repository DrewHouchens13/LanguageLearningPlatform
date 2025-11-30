"""
Tests for Colors lesson management command and integration.
"""
import json

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from home.models import Lesson, LessonAttempt


class TestColorsLessonManagementCommand(TestCase):
    """Test create_colors_lesson management command"""

    def test_create_colors_lesson_command(self):
        """Test management command creates colors lesson with all data"""
        call_command('create_colors_lesson')

        # Verify lesson was created
        lesson = Lesson.objects.get(title='Colors in Spanish')
        self.assertEqual(lesson.language, 'Spanish')
        self.assertEqual(lesson.difficulty_level, 1)
        self.assertEqual(lesson.slug, 'colors')
        self.assertEqual(lesson.order, 2)
        self.assertTrue(lesson.is_published)

        # Verify flashcards were created
        cards = list(lesson.cards.all())
        self.assertEqual(len(cards), 10)

        # Check specific color cards
        red_card = lesson.cards.get(front_text='Red')
        self.assertEqual(red_card.back_text, 'Rojo')
        self.assertEqual(red_card.order, 1)

        blue_card = lesson.cards.get(front_text='Blue')
        self.assertEqual(blue_card.back_text, 'Azul')
        self.assertEqual(blue_card.order, 2)

        white_card = lesson.cards.get(front_text='White')
        self.assertEqual(white_card.back_text, 'Blanco')
        self.assertEqual(white_card.order, 10)

        # Verify quiz questions were created
        questions = list(lesson.quiz_questions.all())
        self.assertEqual(len(questions), 8)

        # Check specific questions
        q1 = questions[0]
        self.assertIn('Red', q1.question)
        self.assertIn('Rojo', q1.options)
        self.assertEqual(q1.correct_index, 1)

        # Check question about "Naranja" (orange)
        orange_q = lesson.quiz_questions.get(question__icontains='orange')
        self.assertEqual(orange_q.options[0], 'Naranja')
        self.assertEqual(orange_q.correct_index, 0)

    def test_create_colors_lesson_idempotent(self):
        """Test command can be run multiple times without errors"""
        # Run command twice
        call_command('create_colors_lesson')
        call_command('create_colors_lesson')

        # Should only create one lesson
        colors_lessons = Lesson.objects.filter(title='Colors in Spanish')
        self.assertEqual(colors_lessons.count(), 1)

        # Should still have correct counts
        lesson = colors_lessons.first()
        self.assertEqual(lesson.cards.count(), 10)
        self.assertEqual(lesson.quiz_questions.count(), 8)

    def test_create_colors_lesson_links_from_shapes(self):
        """Test colors lesson is linked as next lesson from shapes"""
        # Create shapes lesson first
        shapes_lesson = Lesson.objects.create(
            title='Shapes in Spanish',
            slug='shapes',
            order=1
        )

        # Create colors lesson
        call_command('create_colors_lesson')

        # Verify link was created
        shapes_lesson.refresh_from_db()
        colors_lesson = Lesson.objects.get(title='Colors in Spanish')
        self.assertEqual(shapes_lesson.next_lesson, colors_lesson)


class TestColorsLessonTemplates(TestCase):
    """Test colors lesson template rendering"""

    def setUp(self):
        """Create colors lesson"""
        self.client = Client()
        call_command('create_colors_lesson')
        self.lesson = Lesson.objects.get(title='Colors in Spanish')

    def test_colors_lesson_detail_view(self):
        """Test colors lesson detail page loads successfully"""
        url = reverse('lesson_detail', args=[self.lesson.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'lessons/lesson_detail.html')

        # Check flashcards are in context
        self.assertEqual(len(response.context['cards']), 10)

    def test_colors_quiz_template(self):
        """Test colors quiz template loads with dynamic slug"""
        url = reverse('lesson_quiz', args=[self.lesson.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'lessons/colors/quiz.html')

        # Check questions are in context
        self.assertEqual(len(response.context['questions']), 8)

    def test_colors_results_template(self):
        """Test colors results template loads with dynamic slug"""
        # Create an attempt first
        attempt = LessonAttempt.objects.create(
            lesson=self.lesson,
            score=6,
            total=8
        )

        url = reverse('lesson_results', args=[self.lesson.id, attempt.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'lessons/colors/results.html')

        # Check context
        self.assertEqual(response.context['lesson'], self.lesson)
        self.assertEqual(response.context['attempt'], attempt)


class TestColorsLessonQuizFlow(TestCase):
    """Test complete quiz flow for colors lesson"""

    def setUp(self):
        """Create colors lesson and user"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        call_command('create_colors_lesson')
        self.lesson = Lesson.objects.get(title='Colors in Spanish')

    def test_colors_quiz_submission_all_correct(self):
        """Test submitting colors quiz with all correct answers"""
        self.client.login(username='testuser', password='testpass123')

        # Get all questions
        questions = list(self.lesson.quiz_questions.all())

        # Prepare all correct answers
        answers = []
        for q in questions:
            answers.append({
                'question_id': q.id,
                'selected_index': q.correct_index
            })

        # Submit quiz
        url = reverse('submit_lesson_quiz', args=[self.lesson.id])
        response = self.client.post(
            url,
            json.dumps({'answers': answers}),
            content_type='application/json'
        )

        # Verify response
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertTrue(json_response['success'])
        self.assertEqual(json_response['score'], 8)
        self.assertEqual(json_response['total'], 8)

        # Verify attempt was created
        attempt = LessonAttempt.objects.get(lesson=self.lesson, user=self.user)
        self.assertEqual(attempt.score, 8)
        self.assertEqual(attempt.percentage, 100.0)

    def test_colors_quiz_submission_mixed_answers(self):
        """Test submitting colors quiz with mixed answers"""
        self.client.login(username='testuser', password='testpass123')

        # Get questions
        questions = list(self.lesson.quiz_questions.all())

        # Prepare mixed answers (first 4 correct, rest wrong)
        answers = []
        for i, q in enumerate(questions):
            if i < 4:
                selected = q.correct_index
            else:
                # Pick wrong answer
                selected = (q.correct_index + 1) % len(q.options)
            answers.append({
                'question_id': q.id,
                'selected_index': selected
            })

        # Submit quiz
        url = reverse('submit_lesson_quiz', args=[self.lesson.id])
        response = self.client.post(
            url,
            json.dumps({'answers': answers}),
            content_type='application/json'
        )

        # Verify response
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['score'], 4)
        self.assertEqual(json_response['total'], 8)

        # Verify attempt
        attempt = LessonAttempt.objects.get(lesson=self.lesson, user=self.user)
        self.assertEqual(attempt.score, 4)
        self.assertEqual(attempt.percentage, 50.0)

    def test_colors_quiz_guest_submission(self):
        """Test guest user can submit colors quiz"""
        # Don't log in - test as guest

        # Get questions
        questions = list(self.lesson.quiz_questions.all())

        # Prepare answers
        answers = []
        for q in questions:
            answers.append({
                'question_id': q.id,
                'selected_index': q.correct_index
            })

        # Submit quiz
        url = reverse('submit_lesson_quiz', args=[self.lesson.id])
        response = self.client.post(
            url,
            json.dumps({'answers': answers}),
            content_type='application/json'
        )

        # Verify response
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertTrue(json_response['success'])

        # Verify attempt was created with no user
        attempt = LessonAttempt.objects.get(lesson=self.lesson)
        self.assertIsNone(attempt.user)
        self.assertEqual(attempt.score, 8)


class TestColorsLessonIntegration(TestCase):
    """Test colors lesson integration with shapes lesson"""

    def setUp(self):
        """Create both shapes and colors lessons"""
        call_command('create_shapes_lesson')
        call_command('create_colors_lesson')
        self.shapes_lesson = Lesson.objects.get(title='Shapes in Spanish')
        self.colors_lesson = Lesson.objects.get(title='Colors in Spanish')

    def test_lesson_progression_shapes_to_colors(self):
        """Test user can progress from shapes to colors lesson"""
        # Verify link exists
        self.assertEqual(self.shapes_lesson.next_lesson, self.colors_lesson)

        # Create attempt for shapes
        attempt = LessonAttempt.objects.create(
            lesson=self.shapes_lesson,
            score=5,
            total=5
        )

        # Visit results page
        client = Client()
        url = reverse('lesson_results', args=[self.shapes_lesson.id, attempt.id])
        response = client.get(url)

        # Verify colors lesson is in context as next lesson
        self.assertEqual(response.context['next_lesson'], self.colors_lesson)

    def test_lessons_list_shows_both_lessons(self):
        """Test lessons list shows both shapes and colors in correct order"""
        client = Client()
        url = reverse('lessons_list')
        response = client.get(url)

        lessons = response.context['selected_language_lessons']
        lesson_objects = [entry['lesson'] for entry in lessons]
        self.assertIn(self.shapes_lesson, lesson_objects)
        self.assertIn(self.colors_lesson, lesson_objects)
        self.assertLess(
            lesson_objects.index(self.shapes_lesson),
            lesson_objects.index(self.colors_lesson)
        )

    def test_colors_lesson_order_is_correct(self):
        """Test colors lesson has correct order (after shapes)"""
        self.assertEqual(self.shapes_lesson.order, 1)
        self.assertEqual(self.colors_lesson.order, 2)

        # Verify query ordering for Spanish lessons only
        lessons = list(
            Lesson.objects.filter(is_published=True, language='Spanish').order_by('order', 'id')
        )
        self.assertIn(self.shapes_lesson, lessons)
        self.assertIn(self.colors_lesson, lessons)
        self.assertLess(lessons.index(self.shapes_lesson), lessons.index(self.colors_lesson))
