"""
Onboarding Service - Business logic for onboarding assessment

This service handles the calculation of user proficiency levels based on
their performance on the onboarding quiz. It uses a cascading algorithm
that ensures users are placed appropriately at A1, A2, or B1 levels.
"""

from home.models import OnboardingQuestion


class OnboardingService:
    """Service for onboarding assessment logic"""
    
    def calculate_proficiency_level(self, answers_data):
        """
        Determine proficiency level based on performance across difficulty tiers.
        
        Args:
            answers_data: List of dicts with 'difficulty_level', 'is_correct', 'difficulty_points'
        
        Returns:
            str: 'A1', 'A2', or 'B1'
        
        Algorithm Logic:
        ----------------
        1. Calculate total score and percentage
        2. Calculate performance at each level
        3. Use cascading logic with minimum thresholds
        
        Scoring Rules:
        - A1 questions: 1 point each (4 questions = 4 points max)
        - A2 questions: 2 points each (3 questions = 6 points max)
        - B1 questions: 3 points each (3 questions = 9 points max)
        - Total possible: 19 points
        
        Level Assignment Logic (Cascading):
        ------------------------------------
        IF user scores < 50% on A1 questions (< 2 out of 4) → A1 (Beginner)
        
        ELSE IF user scores ≥ 50% on A1 AND < 60% overall → A1 (Beginner)
        
        ELSE IF user scores ≥ 60% overall AND ≥ 50% on A2 questions → A2 (Elementary)
        
        ELSE IF user scores ≥ 70% overall AND ≥ 60% on B1 questions → B1 (Intermediate)
        
        ELSE → A2 (default intermediate case)
        
        Examples:
        ---------
        - Scores 2/4 A1, 0/3 A2, 0/3 B1 = 2/19 (10.5%) → A1
        - Scores 4/4 A1, 2/3 A2, 0/3 B1 = 10/19 (52.6%) → A2 (good A1, some A2)
        - Scores 4/4 A1, 3/3 A2, 1/3 B1 = 16/19 (84.2%) → B1 (needs 60%+ on B1)
        - Scores 4/4 A1, 3/3 A2, 2/3 B1 = 19/19 (100%) → B1
        
        Why This Works:
        - Progressive difficulty ensures proper placement
        - Can't skip levels (must pass A1 to get A2)
        - Prevents false positives (lucky guesses on hard questions)
        - Conservative: better to place lower and let AI lessons elevate them
        """
        
        # Separate scores by level
        a1_correct = sum(1 for a in answers_data if a['difficulty_level'] == 'A1' and a['is_correct'])
        a1_total = sum(1 for a in answers_data if a['difficulty_level'] == 'A1')
        
        a2_correct = sum(1 for a in answers_data if a['difficulty_level'] == 'A2' and a['is_correct'])
        a2_total = sum(1 for a in answers_data if a['difficulty_level'] == 'A2')
        
        b1_correct = sum(1 for a in answers_data if a['difficulty_level'] == 'B1' and a['is_correct'])
        b1_total = sum(1 for a in answers_data if a['difficulty_level'] == 'B1')
        
        # Calculate percentages
        a1_pct = (a1_correct / a1_total * 100) if a1_total > 0 else 0
        a2_pct = (a2_correct / a2_total * 100) if a2_total > 0 else 0
        b1_pct = (b1_correct / b1_total * 100) if b1_total > 0 else 0
        
        # Calculate total score
        total_score = sum(a['difficulty_points'] for a in answers_data if a['is_correct'])
        total_possible = sum(a['difficulty_points'] for a in answers_data)
        overall_pct = (total_score / total_possible * 100) if total_possible > 0 else 0
        
        # Cascading level assignment
        if a1_pct < 50:
            return 'A1'  # Struggling with basics
        
        if overall_pct < 60:
            return 'A1'  # Less than 60% overall = beginner
        
        if a2_pct >= 50 and overall_pct >= 60:
            if b1_pct >= 60 and overall_pct >= 70:
                return 'B1'  # Strong performance including B1 questions
            return 'A2'  # Solid A1/A2, not ready for B1
        
        return 'A2'  # Default safe placement
    
    def get_questions_for_language(self, language='Spanish'):
        """
        Retrieve 10 questions for specified language, ordered by question_number.
        
        Args:
            language: Target language (default: Spanish)
        
        Returns:
            QuerySet of OnboardingQuestion objects
        """
        return OnboardingQuestion.objects.filter(language=language).order_by('question_number')
    
    def analyze_weak_areas(self, answers_data):
        """
        Identify weak areas based on incorrect answers.
        
        This can be used by future AI lesson system to target specific skills.
        
        Args:
            answers_data: List of dicts with 'difficulty_level', 'is_correct', 'question_number'
        
        Returns:
            dict: Summary of weak areas by level
        """
        weak_areas = {
            'A1': [],
            'A2': [],
            'B1': []
        }
        
        for answer in answers_data:
            if not answer['is_correct']:
                level = answer['difficulty_level']
                weak_areas[level].append(answer.get('question_number', 'Unknown'))
        
        return {
            'weak_levels': [level for level, questions in weak_areas.items() if questions],
            'details': weak_areas
        }

