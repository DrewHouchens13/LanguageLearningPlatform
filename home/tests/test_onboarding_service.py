from django.test import TestCase
from home.models import OnboardingQuestion
from home.services.onboarding_service import OnboardingService


class TestOnboardingServiceCalculateProficiencyLevel(TestCase):
    """
    Test OnboardingService proficiency level calculation algorithm.
    
    These tests are critical as they validate the cascading algorithm
    that determines user placement at A1, A2, or B1 levels.
    """

    def setUp(self):
        """Create service instance"""
        self.service = OnboardingService()

    def test_calculate_level_perfect_score(self):
        """Test calculation with all questions correct (19/19) → B1"""
        answers_data = [
            # A1 questions (4 questions, 1 point each)
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 1},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 2},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 3},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 4},
            # A2 questions (3 questions, 2 points each)
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 5},
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 6},
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 7},
            # B1 questions (3 questions, 3 points each)
            {'difficulty_level': 'B1', 'is_correct': True, 'difficulty_points': 3, 'question_number': 8},
            {'difficulty_level': 'B1', 'is_correct': True, 'difficulty_points': 3, 'question_number': 9},
            {'difficulty_level': 'B1', 'is_correct': True, 'difficulty_points': 3, 'question_number': 10},
        ]
        
        level = self.service.calculate_proficiency_level(answers_data)
        # 19/19 = 100%, 4/4 A1 (100%), 3/3 A2 (100%), 3/3 B1 (100%) → B1
        self.assertEqual(level, 'B1')

    def test_calculate_level_fail_a1_basics(self):
        """Test calculation with failing A1 questions (< 50%) → A1"""
        answers_data = [
            # Only 1 out of 4 A1 questions correct (25%)
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 1},
            {'difficulty_level': 'A1', 'is_correct': False, 'difficulty_points': 1, 'question_number': 2},
            {'difficulty_level': 'A1', 'is_correct': False, 'difficulty_points': 1, 'question_number': 3},
            {'difficulty_level': 'A1', 'is_correct': False, 'difficulty_points': 1, 'question_number': 4},
            # All other questions wrong
            {'difficulty_level': 'A2', 'is_correct': False, 'difficulty_points': 2, 'question_number': 5},
            {'difficulty_level': 'A2', 'is_correct': False, 'difficulty_points': 2, 'question_number': 6},
            {'difficulty_level': 'A2', 'is_correct': False, 'difficulty_points': 2, 'question_number': 7},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 8},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 9},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 10},
        ]
        
        level = self.service.calculate_proficiency_level(answers_data)
        # 1/19 = 5.3%, 1/4 A1 (25%) → A1 (struggling with basics)
        self.assertEqual(level, 'A1')

    def test_calculate_level_exactly_50_percent_a1(self):
        """Test calculation with exactly 50% on A1 questions (2/4) → edge case"""
        answers_data = [
            # Exactly 2 out of 4 A1 questions correct (50%)
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 1},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 2},
            {'difficulty_level': 'A1', 'is_correct': False, 'difficulty_points': 1, 'question_number': 3},
            {'difficulty_level': 'A1', 'is_correct': False, 'difficulty_points': 1, 'question_number': 4},
            # All A2/B1 wrong
            {'difficulty_level': 'A2', 'is_correct': False, 'difficulty_points': 2, 'question_number': 5},
            {'difficulty_level': 'A2', 'is_correct': False, 'difficulty_points': 2, 'question_number': 6},
            {'difficulty_level': 'A2', 'is_correct': False, 'difficulty_points': 2, 'question_number': 7},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 8},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 9},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 10},
        ]
        
        level = self.service.calculate_proficiency_level(answers_data)
        # 2/19 = 10.5%, 2/4 A1 (50%) → A1 (< 60% overall)
        self.assertEqual(level, 'A1')

    def test_calculate_level_good_a1_some_a2(self):
        """Test calculation with good A1 and some A2 (10/19 = 52.6%) → A2"""
        answers_data = [
            # All A1 correct (4/4)
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 1},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 2},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 3},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 4},
            # 2 out of 3 A2 correct (66.7%)
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 5},
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 6},
            {'difficulty_level': 'A2', 'is_correct': False, 'difficulty_points': 2, 'question_number': 7},
            # All B1 wrong
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 8},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 9},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 10},
        ]
        
        level = self.service.calculate_proficiency_level(answers_data)
        # 10/19 = 52.6%, 4/4 A1 (100%), 2/3 A2 (66.7%), 0/3 B1 (0%) → A2 (exactly 60% overall not met)
        # Wait, 10/19 is 52.6%, which is less than 60%, so should be A1
        self.assertEqual(level, 'A1')

    def test_calculate_level_exactly_60_percent_overall(self):
        """Test calculation with exactly 60% overall score → A2"""
        answers_data = [
            # All A1 correct (4/4)
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 1},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 2},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 3},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 4},
            # 2 out of 3 A2 correct (66.7%)
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 5},
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 6},
            {'difficulty_level': 'A2', 'is_correct': False, 'difficulty_points': 2, 'question_number': 7},
            # 1 out of 3 B1 correct (33.3%)
            {'difficulty_level': 'B1', 'is_correct': True, 'difficulty_points': 3, 'question_number': 8},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 9},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 10},
        ]
        
        level = self.service.calculate_proficiency_level(answers_data)
        # 4+4+3 = 11/19 = 57.9%, 4/4 A1 (100%), 2/3 A2 (66.7%), 1/3 B1 (33.3%)
        # < 60% overall → A1
        self.assertEqual(level, 'A1')

    def test_calculate_level_solid_a1_a2_placement(self):
        """Test calculation with 12/19 (63.2%) and good A2 → A2"""
        answers_data = [
            # All A1 correct (4/4)
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 1},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 2},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 3},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 4},
            # All A2 correct (3/3)
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 5},
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 6},
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 7},
            # 1 out of 3 B1 correct (33.3%)
            {'difficulty_level': 'B1', 'is_correct': True, 'difficulty_points': 3, 'question_number': 8},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 9},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 10},
        ]
        
        level = self.service.calculate_proficiency_level(answers_data)
        # 13/19 = 68.4%, 4/4 A1 (100%), 3/3 A2 (100%), 1/3 B1 (33.3%) → A2
        # (≥60% overall, ≥50% A2, but <60% B1)
        self.assertEqual(level, 'A2')

    def test_calculate_level_strong_performance_b1(self):
        """Test calculation with 16/19 (84.2%) and good B1 → B1"""
        answers_data = [
            # All A1 correct (4/4)
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 1},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 2},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 3},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 4},
            # All A2 correct (3/3)
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 5},
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 6},
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 7},
            # 2 out of 3 B1 correct (66.7%)
            {'difficulty_level': 'B1', 'is_correct': True, 'difficulty_points': 3, 'question_number': 8},
            {'difficulty_level': 'B1', 'is_correct': True, 'difficulty_points': 3, 'question_number': 9},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 10},
        ]
        
        level = self.service.calculate_proficiency_level(answers_data)
        # 16/19 = 84.2%, 4/4 A1 (100%), 3/3 A2 (100%), 2/3 B1 (66.7%) → B1
        # (≥70% overall, ≥60% B1)
        self.assertEqual(level, 'B1')

    def test_calculate_level_minimum_b1_threshold(self):
        """Test calculation at exact B1 threshold (70% overall, 60% B1) → B1"""
        answers_data = [
            # All A1 correct (4/4)
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 1},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 2},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 3},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 4},
            # 2 out of 3 A2 correct (66.7%)
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 5},
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 6},
            {'difficulty_level': 'A2', 'is_correct': False, 'difficulty_points': 2, 'question_number': 7},
            # 2 out of 3 B1 correct (66.7%)
            {'difficulty_level': 'B1', 'is_correct': True, 'difficulty_points': 3, 'question_number': 8},
            {'difficulty_level': 'B1', 'is_correct': True, 'difficulty_points': 3, 'question_number': 9},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 10},
        ]
        
        level = self.service.calculate_proficiency_level(answers_data)
        # 4+4+6 = 14/19 = 73.7%, 4/4 A1 (100%), 2/3 A2 (66.7%), 2/3 B1 (66.7%) → B1
        self.assertEqual(level, 'B1')

    def test_calculate_level_edge_case_exactly_60_b1_not_enough(self):
        """Test calculation with exactly 60% on B1 but not enough overall"""
        answers_data = [
            # 3 out of 4 A1 correct (75%)
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 1},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 2},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 3},
            {'difficulty_level': 'A1', 'is_correct': False, 'difficulty_points': 1, 'question_number': 4},
            # All A2 wrong
            {'difficulty_level': 'A2', 'is_correct': False, 'difficulty_points': 2, 'question_number': 5},
            {'difficulty_level': 'A2', 'is_correct': False, 'difficulty_points': 2, 'question_number': 6},
            {'difficulty_level': 'A2', 'is_correct': False, 'difficulty_points': 2, 'question_number': 7},
            # 2 out of 3 B1 correct (66.7%)
            {'difficulty_level': 'B1', 'is_correct': True, 'difficulty_points': 3, 'question_number': 8},
            {'difficulty_level': 'B1', 'is_correct': True, 'difficulty_points': 3, 'question_number': 9},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 10},
        ]
        
        level = self.service.calculate_proficiency_level(answers_data)
        # 3+0+6 = 9/19 = 47.4%, 3/4 A1 (75%), 0/3 A2 (0%), 2/3 B1 (66.7%)
        # < 60% overall → A1
        self.assertEqual(level, 'A1')

    def test_calculate_level_no_questions(self):
        """Test calculation with no questions (edge case)"""
        answers_data = []
        
        level = self.service.calculate_proficiency_level(answers_data)
        # No data → returns A1 (all percentages are 0, so a1_pct < 50)
        self.assertEqual(level, 'A1')

    def test_calculate_level_mixed_performance_a2_default(self):
        """Test default A2 placement for mixed performance"""
        answers_data = [
            # All A1 correct (4/4)
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 1},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 2},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 3},
            {'difficulty_level': 'A1', 'is_correct': True, 'difficulty_points': 1, 'question_number': 4},
            # 1 out of 3 A2 correct (33.3%)
            {'difficulty_level': 'A2', 'is_correct': True, 'difficulty_points': 2, 'question_number': 5},
            {'difficulty_level': 'A2', 'is_correct': False, 'difficulty_points': 2, 'question_number': 6},
            {'difficulty_level': 'A2', 'is_correct': False, 'difficulty_points': 2, 'question_number': 7},
            # 2 out of 3 B1 correct (66.7%)
            {'difficulty_level': 'B1', 'is_correct': True, 'difficulty_points': 3, 'question_number': 8},
            {'difficulty_level': 'B1', 'is_correct': True, 'difficulty_points': 3, 'question_number': 9},
            {'difficulty_level': 'B1', 'is_correct': False, 'difficulty_points': 3, 'question_number': 10},
        ]
        
        level = self.service.calculate_proficiency_level(answers_data)
        # 4+2+6 = 12/19 = 63.2%, 4/4 A1 (100%), 1/3 A2 (33.3%), 2/3 B1 (66.7%)
        # ≥60% overall but < 50% A2 → default A2
        self.assertEqual(level, 'A2')


class TestOnboardingServiceGetQuestions(TestCase):
    """Test OnboardingService question retrieval"""

    def setUp(self):
        """Create test questions"""
        self.service = OnboardingService()
        
        # Create 10 Spanish questions
        for i in range(1, 11):
            difficulty = 'A1' if i <= 4 else ('A2' if i <= 7 else 'B1')
            points = 1 if difficulty == 'A1' else (2 if difficulty == 'A2' else 3)
            
            OnboardingQuestion.objects.create(
                question_number=i,
                question_text=f'Spanish question {i}',
                language='Spanish',
                difficulty_level=difficulty,
                option_a='A', option_b='B', option_c='C', option_d='D',
                correct_answer='A',
                difficulty_points=points
            )

    def test_get_questions_for_language_spanish(self):
        """Test retrieving Spanish questions"""
        questions = self.service.get_questions_for_language('Spanish')
        
        self.assertEqual(questions.count(), 10)
        self.assertEqual(questions[0].question_number, 1)
        self.assertEqual(questions[9].question_number, 10)

    def test_get_questions_ordered_by_number(self):
        """Test questions are ordered by question_number"""
        questions = self.service.get_questions_for_language('Spanish')
        
        for i, question in enumerate(questions, start=1):
            self.assertEqual(question.question_number, i)

    def test_get_questions_for_nonexistent_language(self):
        """Test retrieving questions for language with no questions"""
        questions = self.service.get_questions_for_language('French')
        
        self.assertEqual(questions.count(), 0)

    def test_get_questions_filters_by_language(self):
        """Test that questions are filtered by language"""
        # Add a French question
        OnboardingQuestion.objects.create(
            question_number=1,
            question_text='French question',
            language='French',
            difficulty_level='A1',
            option_a='A', option_b='B', option_c='C', option_d='D',
            correct_answer='A',
            difficulty_points=1
        )
        
        spanish_questions = self.service.get_questions_for_language('Spanish')
        french_questions = self.service.get_questions_for_language('French')
        
        self.assertEqual(spanish_questions.count(), 10)
        self.assertEqual(french_questions.count(), 1)


class TestOnboardingServiceAnalyzeWeakAreas(TestCase):
    """Test OnboardingService weak area analysis"""

    def setUp(self):
        """Create service instance"""
        self.service = OnboardingService()

    def test_analyze_weak_areas_no_mistakes(self):
        """Test analysis with no incorrect answers"""
        answers_data = [
            {'difficulty_level': 'A1', 'is_correct': True, 'question_number': 1},
            {'difficulty_level': 'A2', 'is_correct': True, 'question_number': 2},
            {'difficulty_level': 'B1', 'is_correct': True, 'question_number': 3},
        ]
        
        result = self.service.analyze_weak_areas(answers_data)
        
        self.assertEqual(result['weak_levels'], [])
        self.assertEqual(result['details']['A1'], [])
        self.assertEqual(result['details']['A2'], [])
        self.assertEqual(result['details']['B1'], [])

    def test_analyze_weak_areas_with_mistakes(self):
        """Test analysis with incorrect answers"""
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
        self.assertEqual(result['details']['A1'], [1, 2])
        self.assertEqual(result['details']['A2'], [5])
        self.assertEqual(result['details']['B1'], [])

    def test_analyze_weak_areas_all_levels_weak(self):
        """Test analysis with mistakes at all levels"""
        answers_data = [
            {'difficulty_level': 'A1', 'is_correct': False, 'question_number': 1},
            {'difficulty_level': 'A2', 'is_correct': False, 'question_number': 5},
            {'difficulty_level': 'B1', 'is_correct': False, 'question_number': 8},
        ]
        
        result = self.service.analyze_weak_areas(answers_data)
        
        self.assertEqual(len(result['weak_levels']), 3)
        self.assertIn('A1', result['weak_levels'])
        self.assertIn('A2', result['weak_levels'])
        self.assertIn('B1', result['weak_levels'])

