"""
Service layer tests - primarily for onboarding level calculation algorithm.
Tests the critical cascading algorithm that determines user proficiency level.
"""
from django.test import TestCase
from home.models import OnboardingQuestion
from home.services.onboarding_service import OnboardingService


class OnboardingServiceTest(TestCase):
    """Test OnboardingService level calculation algorithm"""
    
    def setUp(self):
        self.service = OnboardingService()
        OnboardingQuestion.objects.filter(language__in=['Spanish', 'French']).delete()
        # Create 10 test questions for get_questions tests
        for i in range(1, 11):
            difficulty = 'A1' if i <= 4 else ('A2' if i <= 7 else 'B1')
            points = 1 if difficulty == 'A1' else (2 if difficulty == 'A2' else 3)
            OnboardingQuestion.objects.create(
                question_number=i, question_text=f'Q{i}', language='Spanish',
                difficulty_level=difficulty, option_a='A', option_b='B',
                option_c='C', option_d='D', correct_answer='A', difficulty_points=points
            )
    
    # =========================================================================
    # LEVEL CALCULATION TESTS - Core Algorithm
    # =========================================================================
    
    def test_perfect_score_gives_b1(self):
        """Test all correct answers → B1"""
        answers = [
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': i}
            for i in range(1, 5)
        ] + [
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': i}
            for i in range(5, 8)
        ] + [
            {'difficulty_level': 'B1', 'is_correct': True, 'difficulty_points': 3, 'question_number': i}
            for i in range(8, 11)
        ]
        level = self.service.calculate_proficiency_level(answers)
        self.assertEqual(level, 'B1')
    
    def test_fail_a1_basics_gives_a1(self):
        """Test failing A1 questions (< 50%) → A1"""
        answers = [
            {'difficulty_level': 'A1', 'is_correct': i < 2, 'difficulty_points': 1, 'question_number': i}
            for i in range(1, 5)
        ] + [
            {'difficulty_level': 'A2', 'is_correct': False, 'difficulty_points': 2, 'question_number': i}
            for i in range(5, 8)
        ] + [
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': i}
            for i in range(8, 11)
        ]
        level = self.service.calculate_proficiency_level(answers)
        self.assertEqual(level, 'A1')
    
    def test_good_a1_and_a2_gives_a2(self):
        """Test solid A1/A2 performance, weak B1 → A2"""
        answers = [
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': i}
            for i in range(1, 5)
        ] + [
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': i}
            for i in range(5, 8)
        ] + [
            {'difficulty_level': 'B1', 'is_correct': i == 8, 'difficulty_points': 3, 'question_number': i}
            for i in range(8, 11)
        ]
        level = self.service.calculate_proficiency_level(answers)
        # 4+6+3 = 13/19 = 68.4%, A1=100%, A2=100%, B1=33% → A2
        self.assertEqual(level, 'A2')
    
    def test_strong_b1_performance_gives_b1(self):
        """Test strong overall + good B1 performance → B1"""
        answers = [
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': i}
            for i in range(1, 5)
        ] + [
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': i}
            for i in range(5, 8)
        ] + [
            {'difficulty_level': 'B1', 'is_correct': i < 10, 'difficulty_points': 3, 'question_number': i}
            for i in range(8, 11)
        ]
        level = self.service.calculate_proficiency_level(answers)
        # 4+6+6 = 16/19 = 84.2%, B1=66.7% → B1
        self.assertEqual(level, 'B1')
    
    def test_below_60_percent_gives_a1(self):
        """Test < 60% overall → A1 (even if A1 questions passed)"""
        answers = [
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': i}
            for i in range(1, 5)
        ] + [
            {'difficulty_level': 'A2', 'is_correct': i == 5, 'difficulty_points': 2, 'question_number': i}
            for i in range(5, 8)
        ] + [
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': i}
            for i in range(8, 11)
        ]
        level = self.service.calculate_proficiency_level(answers)
        # 4+2+0 = 6/19 = 31.6% → A1
        self.assertEqual(level, 'A1')
    
    def test_edge_case_exact_thresholds(self):
        """Test exact threshold boundaries"""
        # 50% A1, 60% overall
        answers = [
            {'difficulty_level': 'A1', 'is_correct': i < 3, 'difficulty_points': 1, 'question_number': i}
            for i in range(1, 5)
        ] + [
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': i}
            for i in range(5, 8)
        ] + [
            {'difficulty_level': 'B1', 'is_correct': i == 8, 'difficulty_points': 3, 'question_number': i}
            for i in range(8, 11)
        ]
        level = self.service.calculate_proficiency_level(answers)
        # 2+6+3 = 11/19 = 57.9% < 60% → A1
        self.assertEqual(level, 'A1')
    
    # =========================================================================
    # QUESTION RETRIEVAL TESTS
    # =========================================================================
    
    def test_get_questions_returns_10_spanish(self):
        """Test retrieving Spanish questions"""
        questions = self.service.get_questions_for_language('Spanish')
        self.assertEqual(questions.count(), 10)
        self.assertEqual(questions[0].question_number, 1)
    
    def test_get_questions_filters_by_language(self):
        """Test language filtering"""
        OnboardingQuestion.objects.filter(language='French').delete()
        OnboardingQuestion.objects.create(
            question_number=1, question_text='French Q', language='French',
            difficulty_level='A1', option_a='A', option_b='B',
            option_c='C', option_d='D', correct_answer='A', difficulty_points=1
        )
        spanish = self.service.get_questions_for_language('Spanish')
        french = self.service.get_questions_for_language('French')
        self.assertEqual(spanish.count(), 10)
        self.assertEqual(french.count(), 1)
    
    # =========================================================================
    # WEAK AREA ANALYSIS TEST
    # =========================================================================
    
    def test_analyze_weak_areas(self):
        """Test weak area identification"""
        answers_data = [
            {'difficulty_level': 'A1', 'is_correct': False, 'question_number': 1},
            {'difficulty_level': 'A1', 'is_correct': False, 'question_number': 2},
            {'difficulty_level': 'A2', 'is_correct': False, 'question_number': 5},
            {'difficulty_level': 'B1', 'is_correct': True, 'question_number': 8},
        ]
        result = self.service.analyze_weak_areas(answers_data)
        self.assertIn('A1', result['weak_levels'])
        self.assertIn('A2', result['weak_levels'])
        self.assertNotIn('B1', result['weak_levels'])

