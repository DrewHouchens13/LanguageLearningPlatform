"""
Model tests - copied from original tests.py with onboarding models added.
Tests for UserProgress, LessonCompletion, QuizResult, UserProfile, 
OnboardingQuestion, OnboardingAttempt, OnboardingAnswer.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import IntegrityError
from datetime import timedelta

from home.models import (
    UserProgress, LessonCompletion, QuizResult,
    UserProfile, OnboardingQuestion, OnboardingAttempt, OnboardingAnswer
)


# ============================================================================
# CORE MODEL TESTS (from original tests.py)
# ============================================================================

class TestUserProgressModel(TestCase):
    """Test UserProgress model functionality"""

    def setUp(self):
        """Create test user and progress record"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.progress = UserProgress.objects.create(
            user=self.user,
            total_minutes_studied=120,
            total_lessons_completed=5,
            total_quizzes_taken=3,
            overall_quiz_accuracy=85.5
        )

    def test_user_progress_creation(self):
        """Test UserProgress is created with correct default values"""
        new_user = User.objects.create_user(username='newuser', email='new@example.com')
        new_progress = UserProgress.objects.create(user=new_user)
        
        self.assertEqual(new_progress.total_minutes_studied, 0)
        self.assertEqual(new_progress.total_lessons_completed, 0)
        self.assertEqual(new_progress.total_quizzes_taken, 0)
        self.assertEqual(new_progress.overall_quiz_accuracy, 0.0)
        self.assertIsNotNone(new_progress.created_at)
        self.assertIsNotNone(new_progress.updated_at)

    def test_user_progress_string_representation(self):
        """Test __str__ method returns correct format"""
        expected = f"Progress for {self.user.username}"
        self.assertEqual(str(self.progress), expected)

    def test_calculate_quiz_accuracy_no_quizzes(self):
        """Test calculate_quiz_accuracy returns 0 when no quizzes exist"""
        accuracy = self.progress.calculate_quiz_accuracy()
        self.assertEqual(accuracy, 0.0)

    def test_calculate_quiz_accuracy_single_quiz(self):
        """Test calculate_quiz_accuracy with one quiz"""
        QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            quiz_title='Basic Spanish',
            score=8,
            total_questions=10
        )
        accuracy = self.progress.calculate_quiz_accuracy()
        self.assertEqual(accuracy, 80.0)

    def test_calculate_quiz_accuracy_multiple_quizzes(self):
        """Test calculate_quiz_accuracy with multiple quizzes"""
        QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            score=8,
            total_questions=10
        )
        QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz2',
            score=15,
            total_questions=20
        )
        # Total: 23/30 = 76.7%
        accuracy = self.progress.calculate_quiz_accuracy()
        self.assertEqual(accuracy, 76.7)

    def test_calculate_quiz_accuracy_zero_total_questions(self):
        """Test calculate_quiz_accuracy handles division by zero"""
        QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            score=0,
            total_questions=0
        )
        accuracy = self.progress.calculate_quiz_accuracy()
        self.assertEqual(accuracy, 0.0)

    def test_get_weekly_stats_current_week(self):
        """Test get_weekly_stats returns correct data for current week"""
        # Create lessons completed this week
        LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson1',
            lesson_title='Lesson 1',
            duration_minutes=30
        )
        LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson2',
            lesson_title='Lesson 2',
            duration_minutes=45
        )
        
        # Create quiz results this week
        QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            score=9,
            total_questions=10
        )
        
        stats = self.progress.get_weekly_stats()
        
        self.assertEqual(stats['weekly_minutes'], 75)
        self.assertEqual(stats['weekly_lessons'], 2)
        self.assertEqual(stats['weekly_accuracy'], 90.0)

    def test_get_weekly_stats_old_data(self):
        """Test get_weekly_stats excludes data older than 7 days"""
        # Create old lesson (8 days ago)
        old_date = timezone.now() - timedelta(days=8)
        old_lesson = LessonCompletion.objects.create(
            user=self.user,
            lesson_id='old_lesson',
            duration_minutes=60
        )
        old_lesson.completed_at = old_date
        old_lesson.save()
        
        stats = self.progress.get_weekly_stats()
        
        self.assertEqual(stats['weekly_minutes'], 0)
        self.assertEqual(stats['weekly_lessons'], 0)
        self.assertEqual(stats['weekly_accuracy'], 0.0)

    def test_get_weekly_stats_no_data(self):
        """Test get_weekly_stats returns zeros when no data exists"""
        stats = self.progress.get_weekly_stats()
        
        self.assertEqual(stats['weekly_minutes'], 0)
        self.assertEqual(stats['weekly_lessons'], 0)
        self.assertEqual(stats['weekly_accuracy'], 0.0)


class TestLessonCompletionModel(TestCase):
    """Test LessonCompletion model functionality"""

    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_lesson_completion_creation(self):
        """Test LessonCompletion is created with correct fields"""
        lesson = LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson_001',
            lesson_title='Introduction to Spanish',
            duration_minutes=25
        )
        
        self.assertEqual(lesson.user, self.user)
        self.assertEqual(lesson.lesson_id, 'lesson_001')
        self.assertEqual(lesson.lesson_title, 'Introduction to Spanish')
        self.assertEqual(lesson.duration_minutes, 25)
        self.assertIsNotNone(lesson.completed_at)

    def test_lesson_completion_ordering(self):
        """Test LessonCompletion ordering is most recent first"""
        lesson1 = LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson1',
            duration_minutes=20
        )
        lesson2 = LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson2',
            duration_minutes=30
        )
        
        lessons = LessonCompletion.objects.all()
        self.assertEqual(lessons[0], lesson2)  # Most recent first
        self.assertEqual(lessons[1], lesson1)

    def test_lesson_completion_user_relationship(self):
        """Test relationship with User model"""
        LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson1',
            duration_minutes=20
        )
        
        self.assertEqual(self.user.lesson_completions.count(), 1)
        self.assertEqual(self.user.lesson_completions.first().lesson_id, 'lesson1')

    def test_lesson_completion_string_representation(self):
        """Test __str__ method returns correct format"""
        lesson = LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson_001',
            lesson_title='Spanish Basics',
            duration_minutes=30
        )
        expected = f"{self.user.username} completed Spanish Basics"
        self.assertEqual(str(lesson), expected)

    def test_lesson_completion_string_without_title(self):
        """Test __str__ method uses lesson_id when title is blank"""
        lesson = LessonCompletion.objects.create(
            user=self.user,
            lesson_id='lesson_001',
            duration_minutes=30
        )
        expected = f"{self.user.username} completed lesson_001"
        self.assertEqual(str(lesson), expected)


class TestQuizResultModel(TestCase):
    """Test QuizResult model functionality"""

    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_quiz_result_creation(self):
        """Test QuizResult is created with correct fields"""
        quiz = QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz_001',
            quiz_title='Spanish Vocabulary Quiz',
            score=18,
            total_questions=20
        )
        
        self.assertEqual(quiz.user, self.user)
        self.assertEqual(quiz.quiz_id, 'quiz_001')
        self.assertEqual(quiz.quiz_title, 'Spanish Vocabulary Quiz')
        self.assertEqual(quiz.score, 18)
        self.assertEqual(quiz.total_questions, 20)
        self.assertIsNotNone(quiz.completed_at)

    def test_quiz_result_accuracy_percentage(self):
        """Test accuracy_percentage property calculation"""
        quiz = QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            score=17,
            total_questions=20
        )
        self.assertEqual(quiz.accuracy_percentage, 85.0)

    def test_quiz_result_accuracy_percentage_zero_questions(self):
        """Test accuracy_percentage handles division by zero"""
        quiz = QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            score=0,
            total_questions=0
        )
        self.assertEqual(quiz.accuracy_percentage, 0.0)

    def test_quiz_result_ordering(self):
        """Test QuizResult ordering is most recent first"""
        quiz1 = QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            score=8,
            total_questions=10
        )
        quiz2 = QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz2',
            score=15,
            total_questions=20
        )
        
        quizzes = QuizResult.objects.all()
        self.assertEqual(quizzes[0], quiz2)  # Most recent first
        self.assertEqual(quizzes[1], quiz1)

    def test_quiz_result_user_relationship(self):
        """Test relationship with User model"""
        QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz1',
            score=8,
            total_questions=10
        )
        
        self.assertEqual(self.user.quiz_results.count(), 1)
        self.assertEqual(self.user.quiz_results.first().quiz_id, 'quiz1')

    def test_quiz_result_string_representation(self):
        """Test __str__ method returns correct format"""
        quiz = QuizResult.objects.create(
            user=self.user,
            quiz_id='quiz_001',
            quiz_title='Vocabulary Test',
            score=18,
            total_questions=20
        )
        expected = f"{self.user.username} - Vocabulary Test: 18/20"
        self.assertEqual(str(quiz), expected)


# ============================================================================
# ONBOARDING MODEL TESTS
# ============================================================================

class TestUserProfileModel(TestCase):
    """Test UserProfile model functionality"""

    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_user_profile_creation_with_defaults(self):
        """Test UserProfile is auto-created with correct default values via signal"""
        # Profile is auto-created by signal when user is created
        profile = self.user.profile

        self.assertEqual(profile.user, self.user)
        self.assertIsNone(profile.proficiency_level)
        self.assertFalse(profile.has_completed_onboarding)
        self.assertIsNone(profile.onboarding_completed_at)
        self.assertEqual(profile.target_language, 'Spanish')
        self.assertEqual(profile.daily_goal_minutes, 15)
        self.assertEqual(profile.learning_motivation, '')
        self.assertIsNotNone(profile.created_at)
        self.assertIsNotNone(profile.updated_at)

    def test_user_profile_with_onboarding_complete(self):
        """Test UserProfile with completed onboarding"""
        completed_time = timezone.now()
        # Use auto-created profile and update it
        profile = self.user.profile
        profile.proficiency_level = 'A2'
        profile.has_completed_onboarding = True
        profile.onboarding_completed_at = completed_time
        profile.target_language = 'Spanish'
        profile.daily_goal_minutes = 30
        profile.learning_motivation = 'Want to travel to Spain'
        profile.save()

        self.assertEqual(profile.proficiency_level, 'A2')
        self.assertTrue(profile.has_completed_onboarding)
        self.assertEqual(profile.onboarding_completed_at, completed_time)
        self.assertEqual(profile.daily_goal_minutes, 30)
        self.assertEqual(profile.learning_motivation, 'Want to travel to Spain')

    def test_user_profile_string_representation(self):
        """Test __str__ method returns correct format"""
        # Use auto-created profile and update it
        profile = self.user.profile
        profile.proficiency_level = 'A1'
        profile.save()
        expected = f"{self.user.username}'s Profile - Beginner (A1)"
        self.assertEqual(str(profile), expected)

    def test_user_profile_string_representation_without_level(self):
        """Test __str__ method for profile without proficiency level"""
        # Use auto-created profile (default has no level)
        profile = self.user.profile
        expected = f"{self.user.username}'s Profile - Not assessed"
        self.assertEqual(str(profile), expected)

    def test_user_profile_one_to_one_relationship(self):
        """Test OneToOne relationship with User"""
        # Use auto-created profile and update it
        profile = self.user.profile
        profile.proficiency_level = 'B1'
        profile.save()

        # Access profile from user
        self.assertEqual(self.user.profile, profile)

    def test_user_profile_unique_constraint(self):
        """Test that only one profile per user can exist (auto-created via signal)"""
        # Profile already exists from signal
        existing_profile = self.user.profile
        self.assertIsNotNone(existing_profile)

        # Attempting to create second profile should raise error
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(user=self.user)

    def test_user_profile_proficiency_level_choices(self):
        """Test proficiency level choices"""
        valid_levels = ['A1', 'A2', 'B1']

        for level in valid_levels:
            # Create new user (which auto-creates profile via signal)
            user = User.objects.create_user(
                username=f'user_{level}',
                email=f'{level}@example.com'
            )
            profile = user.profile
            profile.proficiency_level = level
            profile.save()
            self.assertEqual(profile.proficiency_level, level)


class TestOnboardingQuestionModel(TestCase):
    """Test OnboardingQuestion model functionality"""

    def test_onboarding_question_creation(self):
        """Test OnboardingQuestion is created with correct fields"""
        question = OnboardingQuestion.objects.create(
            question_number=1,
            question_text='What is the Spanish word for "hello"?',
            language='Spanish',
            difficulty_level='A1',
            option_a='Adiós',
            option_b='Hola',
            option_c='Gracias',
            option_d='Por favor',
            correct_answer='B',
            explanation='Hola is the most common greeting in Spanish.',
            difficulty_points=1
        )
        
        self.assertEqual(question.question_number, 1)
        self.assertEqual(question.question_text, 'What is the Spanish word for "hello"?')
        self.assertEqual(question.language, 'Spanish')
        self.assertEqual(question.difficulty_level, 'A1')
        self.assertEqual(question.option_b, 'Hola')
        self.assertEqual(question.correct_answer, 'B')
        self.assertEqual(question.difficulty_points, 1)

    def test_onboarding_question_string_representation(self):
        """Test __str__ method returns correct format"""
        question = OnboardingQuestion.objects.create(
            question_number=1,
            question_text='What is the Spanish word for "hello"?',
            language='Spanish',
            difficulty_level='A1',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='B'
        )
        
        expected = 'Q1 (Spanish - A1): What is the Spanish word for "hello"?...'
        self.assertEqual(str(question), expected)

    def test_onboarding_question_unique_constraint(self):
        """Test (language, question_number) unique constraint"""
        OnboardingQuestion.objects.create(
            question_number=1,
            question_text='First question',
            language='Spanish',
            difficulty_level='A1',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A'
        )
        
        # Attempting to create duplicate should raise error
        with self.assertRaises(IntegrityError):
            OnboardingQuestion.objects.create(
                question_number=1,
                question_text='Different question',
                language='Spanish',
                difficulty_level='A2',
                option_a='A', option_b='B', option_c='C', option_d='D',
                correct_answer='B'
            )

    def test_onboarding_question_different_languages_same_number(self):
        """Test same question number allowed for different languages"""
        OnboardingQuestion.objects.create(
            question_number=1,
            question_text='Spanish question',
            language='Spanish',
            difficulty_level='A1',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A'
        )
        
        # Should allow same question_number for different language
        french_question = OnboardingQuestion.objects.create(
            question_number=1,
            question_text='French question',
            language='French',
            difficulty_level='A1',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A'
        )
        
        self.assertIsNotNone(french_question)

    def test_onboarding_question_ordering(self):
        """Test questions are ordered by language then question_number"""
        OnboardingQuestion.objects.create(
            question_number=2, question_text='Q2', language='Spanish',
            difficulty_level='A1', option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A'
        )
        OnboardingQuestion.objects.create(
            question_number=1, question_text='Q1', language='Spanish',
            difficulty_level='A1', option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A'
        )
        
        questions = OnboardingQuestion.objects.filter(language='Spanish')
        self.assertEqual(questions[0].question_number, 1)
        self.assertEqual(questions[1].question_number, 2)


class TestOnboardingAttemptModel(TestCase):
    """Test OnboardingAttempt model functionality"""

    def setUp(self):
        """Create test user"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_onboarding_attempt_creation_authenticated(self):
        """Test OnboardingAttempt creation for authenticated user"""
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        self.assertEqual(attempt.user, self.user)
        self.assertEqual(attempt.language, 'Spanish')
        self.assertIsNotNone(attempt.started_at)
        self.assertIsNone(attempt.completed_at)
        self.assertEqual(attempt.calculated_level, '')
        self.assertEqual(attempt.total_score, 0)
        self.assertEqual(attempt.total_possible, 0)

    def test_onboarding_attempt_creation_guest(self):
        """Test OnboardingAttempt creation for guest user"""
        attempt = OnboardingAttempt.objects.create(
            session_key='abc123xyz789',
            language='Spanish'
        )
        
        self.assertIsNone(attempt.user)
        self.assertEqual(attempt.session_key, 'abc123xyz789')

    def test_onboarding_attempt_with_results(self):
        """Test OnboardingAttempt with completed results"""
        completed_time = timezone.now()
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish',
            calculated_level='A2',
            total_score=12,
            total_possible=19,
            completed_at=completed_time
        )
        
        self.assertEqual(attempt.calculated_level, 'A2')
        self.assertEqual(attempt.total_score, 12)
        self.assertEqual(attempt.total_possible, 19)
        self.assertEqual(attempt.completed_at, completed_time)

    def test_onboarding_attempt_score_percentage(self):
        """Test score_percentage property calculation"""
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish',
            calculated_level='A2',
            total_score=12,
            total_possible=19
        )
        
        # 12/19 = 63.15... rounded to 63.2
        self.assertEqual(attempt.score_percentage, 63.2)

    def test_onboarding_attempt_score_percentage_zero_total(self):
        """Test score_percentage handles zero total_possible"""
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        self.assertEqual(attempt.score_percentage, 0.0)

    def test_onboarding_attempt_string_representation_authenticated(self):
        """Test __str__ method for authenticated user"""
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish',
            calculated_level='A2'
        )
        
        expected = f"{self.user.username} - Spanish (A2)"
        self.assertEqual(str(attempt), expected)

    def test_onboarding_attempt_string_representation_guest(self):
        """Test __str__ method for guest user"""
        attempt = OnboardingAttempt.objects.create(
            session_key='abc123xyz789',
            language='Spanish',
            calculated_level='A1'
        )
        
        expected = "Guest-abc123xy - Spanish (A1)"
        self.assertEqual(str(attempt), expected)

    def test_onboarding_attempt_string_representation_in_progress(self):
        """Test __str__ method for in-progress attempt"""
        attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        expected = f"{self.user.username} - Spanish (In Progress)"
        self.assertEqual(str(attempt), expected)

    def test_onboarding_attempt_ordering(self):
        """Test attempts are ordered by most recent first"""
        attempt1 = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        attempt2 = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )
        
        attempts = OnboardingAttempt.objects.all()
        self.assertEqual(attempts[0], attempt2)
        self.assertEqual(attempts[1], attempt1)


class TestOnboardingAnswerModel(TestCase):
    """Test OnboardingAnswer model functionality"""

    def setUp(self):
        """Create test user, question, and attempt"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.question = OnboardingQuestion.objects.create(
            question_number=1,
            question_text='What is the Spanish word for "hello"?',
            language='Spanish',
            difficulty_level='A1',
            option_a='Adiós',
            option_b='Hola',
            option_c='Gracias',
            option_d='Por favor',
            correct_answer='B',
            difficulty_points=1
        )
        self.attempt = OnboardingAttempt.objects.create(
            user=self.user,
            language='Spanish'
        )

    def test_onboarding_answer_creation_correct(self):
        """Test OnboardingAnswer creation with correct answer"""
        answer = OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            user_answer='B',
            is_correct=True,
            time_taken_seconds=15
        )
        
        self.assertEqual(answer.attempt, self.attempt)
        self.assertEqual(answer.question, self.question)
        self.assertEqual(answer.user_answer, 'B')
        self.assertTrue(answer.is_correct)
        self.assertEqual(answer.time_taken_seconds, 15)
        self.assertIsNotNone(answer.answered_at)

    def test_onboarding_answer_creation_incorrect(self):
        """Test OnboardingAnswer creation with incorrect answer"""
        answer = OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            user_answer='A',
            is_correct=False,
            time_taken_seconds=10
        )
        
        self.assertEqual(answer.user_answer, 'A')
        self.assertFalse(answer.is_correct)

    def test_onboarding_answer_string_representation_correct(self):
        """Test __str__ method for correct answer"""
        answer = OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            user_answer='B',
            is_correct=True
        )
        
        expected = "✓ Q1 - B"
        self.assertEqual(str(answer), expected)

    def test_onboarding_answer_string_representation_incorrect(self):
        """Test __str__ method for incorrect answer"""
        answer = OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            user_answer='A',
            is_correct=False
        )
        
        expected = "✗ Q1 - A"
        self.assertEqual(str(answer), expected)

    def test_onboarding_answer_related_name(self):
        """Test related_name for answers on attempt"""
        OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            user_answer='B',
            is_correct=True
        )
        
        self.assertEqual(self.attempt.answers.count(), 1)
        self.assertEqual(self.attempt.answers.first().user_answer, 'B')

    def test_onboarding_answer_ordering(self):
        """Test answers are ordered by question number"""
        question2 = OnboardingQuestion.objects.create(
            question_number=2,
            question_text='Second question',
            language='Spanish',
            difficulty_level='A1',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A',
            difficulty_points=1
        )
        
        answer2 = OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=question2,
            user_answer='A',
            is_correct=True
        )
        answer1 = OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            user_answer='B',
            is_correct=True
        )
        
        answers = self.attempt.answers.all()
        self.assertEqual(answers[0].question.question_number, 1)
        self.assertEqual(answers[1].question.question_number, 2)

    def test_onboarding_answer_cascade_delete_on_attempt(self):
        """Test answers are deleted when attempt is deleted"""
        OnboardingAnswer.objects.create(
            attempt=self.attempt,
            question=self.question,
            user_answer='B',
            is_correct=True
        )
        
        attempt_id = self.attempt.id
        self.attempt.delete()
        
        # Answers should be deleted
        self.assertEqual(
            OnboardingAnswer.objects.filter(attempt_id=attempt_id).count(),
            0
        )
