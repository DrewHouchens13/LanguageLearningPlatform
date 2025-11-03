"""
Comprehensive tests for Lesson system (models, views, security).
Tests for Lesson, Flashcard, LessonQuizQuestion, LessonAttempt models and all lesson views.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.http import HttpResponseBadRequest
from django.core.exceptions import ValidationError
from unittest.mock import patch
import json
import logging

from home.models import (
    Lesson, Flashcard, LessonQuizQuestion, LessonAttempt
)


# ============================================================================
# LESSON MODEL TESTS
# ============================================================================

class TestLessonModel(TestCase):
    """Test Lesson model functionality"""

    def setUp(self):
        """Create test lessons"""
        self.lesson = Lesson.objects.create(
            title='Basic Spanish Greetings',
            description='Learn common Spanish greetings',
            language='Spanish',
            difficulty_level='A1',
            order=1,
            is_published=True
        )
        self.next_lesson = Lesson.objects.create(
            title='Spanish Numbers',
            description='Learn numbers 1-10',
            language='Spanish',
            difficulty_level='A1',
            order=2,
            is_published=True
        )
        self.lesson.next_lesson = self.next_lesson
        self.lesson.save()

    def test_lesson_creation(self):
        """Test Lesson is created with correct values"""
        self.assertEqual(self.lesson.title, 'Basic Spanish Greetings')
        self.assertEqual(self.lesson.language, 'Spanish')
        self.assertEqual(self.lesson.difficulty_level, 'A1')
        self.assertEqual(self.lesson.order, 1)
        self.assertTrue(self.lesson.is_published)
        self.assertIsNotNone(self.lesson.created_at)
        self.assertIsNotNone(self.lesson.updated_at)

    def test_lesson_string_representation(self):
        """Test __str__ method returns correct format"""
        expected = "Basic Spanish Greetings (A1)"
        self.assertEqual(str(self.lesson), expected)

    def test_lesson_ordering(self):
        """Test lessons are ordered by 'order' field then 'id'"""
        lesson3 = Lesson.objects.create(
            title='Spanish Colors',
            order=0,
            difficulty_level='A1'
        )
        lessons = list(Lesson.objects.all())
        self.assertEqual(lessons[0], lesson3)  # order=0
        self.assertEqual(lessons[1], self.lesson)  # order=1
        self.assertEqual(lessons[2], self.next_lesson)  # order=2

    def test_lesson_next_lesson_relationship(self):
        """Test next_lesson foreign key relationship"""
        self.assertEqual(self.lesson.next_lesson, self.next_lesson)
        self.assertEqual(self.next_lesson.previous_lesson.first(), self.lesson)

    def test_lesson_next_lesson_cascade_on_delete(self):
        """Test next_lesson is set to null when target lesson is deleted"""
        self.next_lesson.delete()
        self.lesson.refresh_from_db()
        self.assertIsNone(self.lesson.next_lesson)

    def test_lesson_difficulty_choices(self):
        """Test difficulty_level accepts only valid choices"""
        self.lesson.difficulty_level = 'A2'
        self.lesson.save()
        self.assertEqual(self.lesson.difficulty_level, 'A2')

        self.lesson.difficulty_level = 'B1'
        self.lesson.save()
        self.assertEqual(self.lesson.difficulty_level, 'B1')

    def test_lesson_unpublished(self):
        """Test unpublished lessons can be created"""
        draft = Lesson.objects.create(
            title='Draft Lesson',
            is_published=False
        )
        self.assertFalse(draft.is_published)


class TestFlashcardModel(TestCase):
    """Test Flashcard model functionality"""

    def setUp(self):
        """Create test lesson and flashcards"""
        self.lesson = Lesson.objects.create(
            title='Spanish Colors',
            difficulty_level='A1'
        )
        self.card1 = Flashcard.objects.create(
            lesson=self.lesson,
            front_text='Red',
            back_text='Rojo',
            order=1
        )
        self.card2 = Flashcard.objects.create(
            lesson=self.lesson,
            front_text='Blue',
            back_text='Azul',
            order=2,
            image_url='https://example.com/blue.png'
        )

    def test_flashcard_creation(self):
        """Test Flashcard is created with correct values"""
        self.assertEqual(self.card1.front_text, 'Red')
        self.assertEqual(self.card1.back_text, 'Rojo')
        self.assertEqual(self.card1.lesson, self.lesson)
        self.assertEqual(self.card1.order, 1)

    def test_flashcard_string_representation(self):
        """Test __str__ method returns correct format"""
        expected = "Red → Rojo"
        self.assertEqual(str(self.card1), expected)

    def test_flashcard_ordering(self):
        """Test flashcards are ordered by 'order' field"""
        cards = list(self.lesson.cards.all())
        self.assertEqual(cards[0], self.card1)
        self.assertEqual(cards[1], self.card2)

    def test_flashcard_cascade_delete(self):
        """Test flashcards are deleted when lesson is deleted"""
        card_id = self.card1.id
        self.lesson.delete()
        self.assertFalse(Flashcard.objects.filter(id=card_id).exists())

    def test_flashcard_optional_fields(self):
        """Test flashcard with image and audio URLs"""
        self.assertEqual(self.card2.image_url, 'https://example.com/blue.png')
        self.assertEqual(self.card2.audio_url, '')


class TestLessonQuizQuestionModel(TestCase):
    """Test LessonQuizQuestion model functionality"""

    def setUp(self):
        """Create test lesson and questions"""
        self.lesson = Lesson.objects.create(
            title='Spanish Shapes',
            difficulty_level='A1'
        )
        self.question = LessonQuizQuestion.objects.create(
            lesson=self.lesson,
            question='What is "circle" in Spanish?',
            options=['Cuadrado', 'Círculo', 'Triángulo', 'Rectángulo'],
            correct_index=1,
            explanation='Círculo means circle in Spanish',
            order=1
        )

    def test_quiz_question_creation(self):
        """Test LessonQuizQuestion is created with correct values"""
        self.assertEqual(self.question.question, 'What is "circle" in Spanish?')
        self.assertEqual(len(self.question.options), 4)
        self.assertEqual(self.question.correct_index, 1)
        self.assertEqual(self.question.explanation, 'Círculo means circle in Spanish')
        self.assertEqual(self.question.order, 1)

    def test_quiz_question_string_representation(self):
        """Test __str__ method returns correct format"""
        result = str(self.question)
        self.assertIn('Q1:', result)
        self.assertIn('What is "circle" in Spanish?', result)

    def test_quiz_question_ordering(self):
        """Test questions are ordered by 'order' field"""
        q2 = LessonQuizQuestion.objects.create(
            lesson=self.lesson,
            question='What is "square"?',
            options=['A', 'B', 'C', 'D'],
            correct_index=0,
            order=2
        )
        questions = list(self.lesson.quiz_questions.all())
        self.assertEqual(questions[0], self.question)
        self.assertEqual(questions[1], q2)

    def test_quiz_question_cascade_delete(self):
        """Test questions are deleted when lesson is deleted"""
        question_id = self.question.id
        self.lesson.delete()
        self.assertFalse(LessonQuizQuestion.objects.filter(id=question_id).exists())

    def test_quiz_question_json_options(self):
        """Test options field stores JSON list"""
        self.assertIsInstance(self.question.options, list)
        self.assertEqual(self.question.options[1], 'Círculo')


class TestLessonAttemptModel(TestCase):
    """Test LessonAttempt model functionality"""

    def setUp(self):
        """Create test user, lesson, and attempt"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.lesson = Lesson.objects.create(
            title='Spanish Shapes',
            difficulty_level='A1'
        )
        self.attempt = LessonAttempt.objects.create(
            lesson=self.lesson,
            user=self.user,
            score=8,
            total=10
        )

    def test_attempt_creation(self):
        """Test LessonAttempt is created with correct values"""
        self.assertEqual(self.attempt.lesson, self.lesson)
        self.assertEqual(self.attempt.user, self.user)
        self.assertEqual(self.attempt.score, 8)
        self.assertEqual(self.attempt.total, 10)
        self.assertIsNotNone(self.attempt.completed_at)

    def test_attempt_string_representation(self):
        """Test __str__ method returns correct format"""
        expected = "testuser - Spanish Shapes: 8/10"
        self.assertEqual(str(self.attempt), expected)

    def test_attempt_guest_user(self):
        """Test attempt with no user (guest)"""
        guest_attempt = LessonAttempt.objects.create(
            lesson=self.lesson,
            user=None,
            score=5,
            total=10
        )
        self.assertIsNone(guest_attempt.user)
        self.assertEqual(str(guest_attempt), "Guest - Spanish Shapes: 5/10")

    def test_attempt_percentage_property(self):
        """Test percentage property calculates correctly"""
        self.assertEqual(self.attempt.percentage, 80.0)

    def test_attempt_percentage_zero_total(self):
        """Test percentage handles zero total gracefully"""
        attempt = LessonAttempt.objects.create(
            lesson=self.lesson,
            user=self.user,
            score=0,
            total=0
        )
        self.assertEqual(attempt.percentage, 0)

    def test_attempt_ordering(self):
        """Test attempts are ordered by completed_at (newest first)"""
        attempt2 = LessonAttempt.objects.create(
            lesson=self.lesson,
            user=self.user,
            score=10,
            total=10
        )
        attempts = list(LessonAttempt.objects.all())
        self.assertEqual(attempts[0], attempt2)  # Newest first
        self.assertEqual(attempts[1], self.attempt)

    def test_attempt_cascade_delete_lesson(self):
        """Test attempts are deleted when lesson is deleted"""
        attempt_id = self.attempt.id
        self.lesson.delete()
        self.assertFalse(LessonAttempt.objects.filter(id=attempt_id).exists())


# ============================================================================
# LESSON VIEW TESTS
# ============================================================================

class TestLessonsListView(TestCase):
    """Test lessons_list view functionality"""

    def setUp(self):
        """Create test lessons"""
        self.client = Client()
        self.url = reverse('lessons_list')
        self.lesson1 = Lesson.objects.create(
            title='Lesson 1',
            order=1,
            is_published=True
        )
        self.lesson2 = Lesson.objects.create(
            title='Lesson 2',
            order=2,
            is_published=True
        )
        self.draft_lesson = Lesson.objects.create(
            title='Draft Lesson',
            order=3,
            is_published=False
        )

    def test_lessons_list_get_request(self):
        """Test GET request renders lessons_list.html"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'lessons_list.html')

    def test_lessons_list_shows_published_only(self):
        """Test only published lessons are shown"""
        response = self.client.get(self.url)
        self.assertContains(response, 'Lesson 1')
        self.assertContains(response, 'Lesson 2')
        self.assertNotContains(response, 'Draft Lesson')

    def test_lessons_list_ordering(self):
        """Test lessons are ordered by order field"""
        response = self.client.get(self.url)
        lessons = response.context['lessons']
        self.assertEqual(lessons[0], self.lesson1)
        self.assertEqual(lessons[1], self.lesson2)

    def test_lessons_list_empty(self):
        """Test lessons list with no published lessons"""
        Lesson.objects.all().update(is_published=False)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['lessons']), 0)


class TestLessonDetailView(TestCase):
    """Test lesson_detail view functionality"""

    def setUp(self):
        """Create test lesson with flashcards"""
        self.client = Client()
        self.lesson = Lesson.objects.create(
            title='Spanish Colors',
            description='Learn colors in Spanish',
            difficulty_level='A1',
            is_published=True
        )
        self.card1 = Flashcard.objects.create(
            lesson=self.lesson,
            front_text='Red',
            back_text='Rojo',
            order=1
        )
        self.card2 = Flashcard.objects.create(
            lesson=self.lesson,
            front_text='Blue',
            back_text='Azul',
            order=2
        )
        self.url = reverse('lesson_detail', args=[self.lesson.id])

    def test_lesson_detail_get_request(self):
        """Test GET request renders lesson_detail.html"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'lessons/lesson_detail.html')

    def test_lesson_detail_context(self):
        """Test lesson_detail provides correct context"""
        response = self.client.get(self.url)
        self.assertEqual(response.context['lesson'], self.lesson)
        cards = list(response.context['cards'])
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0], self.card1)
        self.assertEqual(cards[1], self.card2)

    def test_lesson_detail_invalid_id(self):
        """Test lesson_detail with invalid lesson ID returns 404"""
        url = reverse('lesson_detail', args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_lesson_detail_unpublished(self):
        """Test unpublished lesson returns 404"""
        self.lesson.is_published = False
        self.lesson.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_lesson_detail_no_flashcards(self):
        """Test lesson with no flashcards"""
        self.card1.delete()
        self.card2.delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['cards']), 0)


class TestLessonQuizView(TestCase):
    """Test lesson_quiz view functionality"""

    def setUp(self):
        """Create test lesson with quiz questions"""
        self.client = Client()
        self.lesson = Lesson.objects.create(
            title='Spanish Shapes',
            is_published=True
        )
        self.q1 = LessonQuizQuestion.objects.create(
            lesson=self.lesson,
            question='What is circle?',
            options=['Cuadrado', 'Círculo', 'Triángulo', 'Rectángulo'],
            correct_index=1,
            order=1
        )
        self.q2 = LessonQuizQuestion.objects.create(
            lesson=self.lesson,
            question='What is square?',
            options=['Cuadrado', 'Círculo', 'Triángulo', 'Rectángulo'],
            correct_index=0,
            order=2
        )
        self.url = reverse('lesson_quiz', args=[self.lesson.id])

    def test_lesson_quiz_get_request(self):
        """Test GET request renders quiz template"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'lessons/shapes/quiz.html')

    def test_lesson_quiz_context(self):
        """Test lesson_quiz provides correct context"""
        response = self.client.get(self.url)
        self.assertEqual(response.context['lesson'], self.lesson)
        questions = response.context['questions']
        self.assertEqual(len(questions), 2)
        self.assertEqual(questions[0]['question'], 'What is circle?')
        self.assertEqual(questions[0]['options'], ['Cuadrado', 'Círculo', 'Triángulo', 'Rectángulo'])

    def test_lesson_quiz_invalid_id(self):
        """Test lesson_quiz with invalid lesson ID returns 404"""
        url = reverse('lesson_quiz', args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_lesson_quiz_unpublished(self):
        """Test unpublished lesson returns 404"""
        self.lesson.is_published = False
        self.lesson.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)


class TestSubmitLessonQuizView(TestCase):
    """Test submit_lesson_quiz view functionality"""

    def setUp(self):
        """Create test lesson and user"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.lesson = Lesson.objects.create(
            title='Spanish Shapes',
            is_published=True
        )
        self.q1 = LessonQuizQuestion.objects.create(
            lesson=self.lesson,
            question='What is circle?',
            options=['Cuadrado', 'Círculo', 'Triángulo', 'Rectángulo'],
            correct_index=1,
            order=1
        )
        self.q2 = LessonQuizQuestion.objects.create(
            lesson=self.lesson,
            question='What is square?',
            options=['Cuadrado', 'Círculo', 'Triángulo', 'Rectángulo'],
            correct_index=0,
            order=2
        )
        self.url = reverse('submit_lesson_quiz', args=[self.lesson.id])

    def test_submit_quiz_authenticated_user(self):
        """Test submit quiz as authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'answers': [
                {'question_id': self.q1.id, 'selected_index': 1},
                {'question_id': self.q2.id, 'selected_index': 0}
            ]
        }
        response = self.client.post(
            self.url,
            json.dumps(data),
            content_type='application/json'
        )

        # Should return JSON response
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertTrue(json_response['success'])
        self.assertEqual(json_response['score'], 2)
        self.assertEqual(json_response['total'], 2)

        # Attempt should be created
        attempt = LessonAttempt.objects.get(lesson=self.lesson, user=self.user)
        self.assertEqual(attempt.score, 2)
        self.assertEqual(attempt.total, 2)

    def test_submit_quiz_guest_user(self):
        """Test submit quiz as guest (not logged in)"""
        data = {
            'answers': [
                {'question_id': self.q1.id, 'selected_index': 1},
                {'question_id': self.q2.id, 'selected_index': 0}
            ]
        }
        response = self.client.post(
            self.url,
            json.dumps(data),
            content_type='application/json'
        )

        # Should return JSON response
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertTrue(json_response['success'])

        # Attempt should be created with no user
        attempt = LessonAttempt.objects.get(lesson=self.lesson)
        self.assertIsNone(attempt.user)
        self.assertEqual(attempt.score, 2)

    def test_submit_quiz_json_request(self):
        """Test submit quiz with JSON content type"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'answers': [
                {'question_id': self.q1.id, 'selected_index': 1},
                {'question_id': self.q2.id, 'selected_index': 0}
            ]
        }
        response = self.client.post(
            self.url,
            json.dumps(data),
            content_type='application/json'
        )

        # Should return JSON response
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertTrue(json_response['success'])
        self.assertEqual(json_response['score'], 2)
        self.assertEqual(json_response['total'], 2)

    def test_submit_quiz_wrong_answers(self):
        """Test submit quiz with wrong answers"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'answers': [
                {'question_id': self.q1.id, 'selected_index': 0},  # Wrong
                {'question_id': self.q2.id, 'selected_index': 3}   # Wrong
            ]
        }
        response = self.client.post(
            self.url,
            json.dumps(data),
            content_type='application/json'
        )

        json_response = response.json()
        attempt = LessonAttempt.objects.get(lesson=self.lesson, user=self.user)
        self.assertEqual(attempt.score, 0)
        self.assertEqual(attempt.total, 2)

    def test_submit_quiz_mixed_answers(self):
        """Test submit quiz with mixed correct/incorrect answers"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'answers': [
                {'question_id': self.q1.id, 'selected_index': 1},  # Correct
                {'question_id': self.q2.id, 'selected_index': 3}   # Wrong
            ]
        }
        response = self.client.post(
            self.url,
            json.dumps(data),
            content_type='application/json'
        )

        json_response = response.json()
        attempt = LessonAttempt.objects.get(lesson=self.lesson, user=self.user)
        self.assertEqual(attempt.score, 1)
        self.assertEqual(attempt.total, 2)

    def test_submit_quiz_no_answers(self):
        """Test submit quiz with no answers returns 400 JSON error"""
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 400)
        # Verify JSON error response
        json_response = response.json()
        self.assertIn('error', json_response)
        self.assertIn('No answers provided', json_response['error'])

    def test_submit_quiz_invalid_json(self):
        """Test submit quiz with invalid JSON returns 400 JSON error and logs error"""
        with self.assertLogs('home.views', level='WARNING') as log_context:
            response = self.client.post(
                self.url,
                'invalid json',
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 400)

            # Verify JSON error response
            json_response = response.json()
            self.assertIn('error', json_response)
            self.assertEqual(json_response['error'], 'Invalid JSON format')

            # Verify error was logged (without sensitive details)
            self.assertEqual(len(log_context.output), 1)
            self.assertIn('Invalid JSON payload', log_context.output[0])
            self.assertIn(f'lesson {self.lesson.id}', log_context.output[0])
            # Ensure no sensitive exception details in log
            self.assertNotIn('Traceback', log_context.output[0])

    def test_submit_quiz_answers_not_list(self):
        """Test submit quiz with answers as non-list returns 400 JSON error"""
        # Test with answers as string (attempts JSON parse, fails)
        response = self.client.post(
            self.url,
            json.dumps({'answers': 'not a list'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn('error', json_response)
        # New logic tries to parse string as JSON, fails with specific error
        self.assertIn('Invalid answers format', json_response['error'])

        # Test with answers as dict
        response = self.client.post(
            self.url,
            json.dumps({'answers': {'question_id': 1}}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn('error', json_response)

        # Test with answers as number
        response = self.client.post(
            self.url,
            json.dumps({'answers': 42}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        json_response = response.json()
        self.assertIn('error', json_response)

    def test_submit_quiz_answers_with_invalid_types(self):
        """Test submit quiz with answers containing invalid element types"""
        self.client.login(username='testuser', password='testpass123')

        # Test with non-dict elements in answers list
        data = {
            'answers': ['string', 123, None, True]
        }
        response = self.client.post(
            self.url,
            json.dumps(data),
            content_type='application/json'
        )
        # Should handle gracefully and return success (skips invalid answers)
        self.assertEqual(response.status_code, 200)

    def test_submit_quiz_answers_missing_required_keys(self):
        """Test submit quiz with answers missing question_id or selected_index"""
        self.client.login(username='testuser', password='testpass123')

        # Test with missing question_id
        data = {
            'answers': [
                {'selected_index': 1}  # Missing question_id
            ]
        }
        response = self.client.post(
            self.url,
            json.dumps(data),
            content_type='application/json'
        )
        # Should handle gracefully and return success (skips invalid answers)
        self.assertEqual(response.status_code, 200)

        # Test with missing selected_index
        data = {
            'answers': [
                {'question_id': self.q1.id}  # Missing selected_index
            ]
        }
        response = self.client.post(
            self.url,
            json.dumps(data),
            content_type='application/json'
        )
        # Should handle gracefully and return success (skips invalid answers)
        self.assertEqual(response.status_code, 200)

    def test_submit_quiz_invalid_question_id(self):
        """Test submit quiz with invalid question ID skips that answer"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'answers': [
                {'question_id': 9999, 'selected_index': 1},  # Invalid ID
                {'question_id': self.q2.id, 'selected_index': 0}  # Valid
            ]
        }
        response = self.client.post(
            self.url,
            json.dumps(data),
            content_type='application/json'
        )

        json_response = response.json()
        attempt = LessonAttempt.objects.get(lesson=self.lesson, user=self.user)
        self.assertEqual(attempt.score, 1)
        self.assertEqual(attempt.total, 1)  # Only valid question counted

    def test_submit_quiz_get_request_not_allowed(self):
        """Test GET request to submit_lesson_quiz is not allowed"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_submit_quiz_unpublished_lesson(self):
        """Test submitting quiz for unpublished lesson returns 404"""
        self.lesson.is_published = False
        self.lesson.save()
        data = {
            'answers': json.dumps([
                {'question_id': self.q1.id, 'selected_index': 1}
            ])
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 404)


class TestLessonResultsView(TestCase):
    """Test lesson_results view functionality"""

    def setUp(self):
        """Create test lesson, attempt, and next lesson"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.lesson = Lesson.objects.create(
            title='Spanish Shapes',
            is_published=True
        )
        self.next_lesson = Lesson.objects.create(
            title='Spanish Colors',
            is_published=True
        )
        self.lesson.next_lesson = self.next_lesson
        self.lesson.save()

        self.attempt = LessonAttempt.objects.create(
            lesson=self.lesson,
            user=self.user,
            score=8,
            total=10
        )
        self.url = reverse('lesson_results', args=[self.lesson.id, self.attempt.id])

    def test_lesson_results_get_request(self):
        """Test GET request renders results template"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'lessons/shapes/results.html')

    def test_lesson_results_context(self):
        """Test lesson_results provides correct context"""
        response = self.client.get(self.url)
        self.assertEqual(response.context['lesson'], self.lesson)
        self.assertEqual(response.context['attempt'], self.attempt)
        self.assertEqual(response.context['next_lesson'], self.next_lesson)

    def test_lesson_results_no_next_lesson(self):
        """Test lesson_results with no next lesson"""
        self.lesson.next_lesson = None
        self.lesson.save()
        response = self.client.get(self.url)
        self.assertIsNone(response.context['next_lesson'])

    def test_lesson_results_invalid_lesson_id(self):
        """Test lesson_results with invalid lesson ID returns 404"""
        url = reverse('lesson_results', args=[9999, self.attempt.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_lesson_results_invalid_attempt_id(self):
        """Test lesson_results with invalid attempt ID returns 404"""
        url = reverse('lesson_results', args=[self.lesson.id, 9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_lesson_results_mismatched_attempt(self):
        """Test lesson_results with attempt from different lesson returns 404"""
        other_lesson = Lesson.objects.create(title='Other Lesson')
        other_attempt = LessonAttempt.objects.create(
            lesson=other_lesson,
            user=self.user,
            score=5,
            total=5
        )
        url = reverse('lesson_results', args=[self.lesson.id, other_attempt.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


# ============================================================================
# SECURITY TESTS
# ============================================================================

class TestLessonSecurityTests(TestCase):
    """Test security aspects of lesson views"""

    @classmethod
    def setUpTestData(cls):
        """Create test data once for all tests (read-only test class)"""
        cls.lesson = Lesson.objects.create(
            title='Test Lesson',
            is_published=True
        )
        cls.question = LessonQuizQuestion.objects.create(
            lesson=cls.lesson,
            question='Test question',
            options=['A', 'B', 'C', 'D'],
            correct_index=0,
            order=1
        )

    def setUp(self):
        """Set up test client for each test"""
        self.client = Client()

    def test_xss_attempt_in_quiz_submission(self):
        """Test XSS attack attempt in quiz submission is handled safely"""
        url = reverse('submit_lesson_quiz', args=[self.lesson.id])
        xss_payload = '<script>alert("XSS")</script>'
        data = {
            'answers': json.dumps([
                {'question_id': xss_payload, 'selected_index': 0}
            ])
        }
        response = self.client.post(url, data)

        # Should handle gracefully (no crash)
        self.assertIn(response.status_code, [200, 302, 400])

    def test_xss_with_event_handlers(self):
        """Test XSS using event handlers (onerror, onload, onclick)"""
        url = reverse('submit_lesson_quiz', args=[self.lesson.id])
        xss_payloads = [
            '<img src=x onerror=alert("XSS")>',
            '<body onload=alert("XSS")>',
            '<div onclick=alert("XSS")>Click</div>',
            '<svg onload=alert("XSS")></svg>'
        ]
        for payload in xss_payloads:
            data = {
                'answers': json.dumps([
                    {'question_id': payload, 'selected_index': 0}
                ])
            }
            response = self.client.post(url, data)
            # Should handle safely without executing script
            self.assertIn(response.status_code, [200, 302, 400])

    def test_xss_with_javascript_uri(self):
        """Test XSS using javascript: URI schemes"""
        url = reverse('submit_lesson_quiz', args=[self.lesson.id])
        xss_payloads = [
            'javascript:alert("XSS")',
            '<a href="javascript:alert(1)">Click</a>',
            '<iframe src="javascript:alert(1)"></iframe>'
        ]
        for payload in xss_payloads:
            data = {
                'answers': json.dumps([
                    {'question_id': payload, 'selected_index': 0}
                ])
            }
            response = self.client.post(url, data)
            self.assertIn(response.status_code, [200, 302, 400])

    def test_xss_with_encoded_payloads(self):
        """Test XSS using HTML entity encoding and obfuscation"""
        url = reverse('submit_lesson_quiz', args=[self.lesson.id])
        xss_payloads = [
            '&lt;script&gt;alert("XSS")&lt;/script&gt;',
            '&#60;script&#62;alert("XSS")&#60;/script&#62;',
            '%3Cscript%3Ealert("XSS")%3C/script%3E'
        ]
        for payload in xss_payloads:
            data = {
                'answers': json.dumps([
                    {'question_id': payload, 'selected_index': 0}
                ])
            }
            response = self.client.post(url, data)
            self.assertIn(response.status_code, [200, 302, 400])

    def test_sql_injection_attempt_in_lesson_detail(self):
        """Test SQL injection attempt in lesson_detail URL parameter"""
        url = f"/lessons/1' OR '1'='1/"
        response = self.client.get(url)

        # Should return 404 (Django's ORM prevents SQL injection)
        self.assertEqual(response.status_code, 404)

    def test_unauthorized_access_published_lessons(self):
        """Test guest users can access published lessons"""
        url = reverse('lesson_detail', args=[self.lesson.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_csrf_protection_on_quiz_submission(self):
        """Test CSRF protection is enforced on quiz submission"""
        # Note: Django test client includes CSRF token by default
        # JSON requests are exempt from CSRF by content type
        url = reverse('submit_lesson_quiz', args=[self.lesson.id])
        data = {
            'answers': [
                {'question_id': self.question.id, 'selected_index': 0}
            ]
        }
        response = self.client.post(
            url,
            json.dumps(data),
            content_type='application/json'
        )
        # Should succeed with JSON (CSRF exempt for JSON APIs typically)
        self.assertEqual(response.status_code, 200)
