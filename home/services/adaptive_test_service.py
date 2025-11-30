"""
Adaptive Test Service for Language Learning Platform.

Generates personalized tests based on user skill mastery:
- 70% questions from weak skills (mastery < 60%)
- 30% questions from strong skills (mastery >= 60%)

Tests are AI-generated using OpenAI to ensure fresh, level-appropriate content.
Users must score 85%+ to advance to the next level.

🤖 AI ASSISTANT: Core service for level progression tests.
- Test composition adapts to individual weaknesses
- 10 questions per test, 85% passing threshold
- 24-hour cooldown on failed attempts
- Level 10 users loop back for continued practice

RELATED FILES:
- home/models.py - UserModuleProgress, UserSkillMastery
- home/views.py - test submission endpoint
- home/templates/curriculum/test.html - test UI
"""

import json
import logging
import os
import random
import re
from datetime import timedelta
from typing import Optional, Dict, List

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class AdaptiveTestService:
    """
    Generate and evaluate personalized adaptive tests.
    
    Usage:
        service = AdaptiveTestService()
        
        # Generate a test
        test = service.generate_adaptive_test(user, 'Spanish', level=3)
        
        # Evaluate answers
        result = service.evaluate_test(user, module, answers)
        if result['passed']:
            print(f"Advanced to level {result['new_level']}!")
    """
    
    TEST_QUESTION_COUNT = 10
    PASSING_SCORE = 85  # Percentage
    RETRY_COOLDOWN_MINUTES = 10  # Changed from 24 hours to 10 minutes
    MAX_LEVEL = 10
    
    # Skill distribution for adaptive tests
    WEAK_SKILL_RATIO = 0.70  # 70% from weak skills
    STRONG_SKILL_RATIO = 0.30  # 30% from strong skills
    WEAK_SKILL_THRESHOLD = 60.0  # Below 60% is considered weak
    
    # Level themes for AI content generation
    LEVEL_THEMES = {
        1: {'name': 'Basics', 'topics': ['greetings', 'numbers 1-10', 'colors', 'basic phrases']},
        2: {'name': 'Daily Life', 'topics': ['family', 'food', 'common objects', 'time']},
        3: {'name': 'Getting Around', 'topics': ['directions', 'transportation', 'places', 'asking for help']},
        4: {'name': 'Social', 'topics': ['introductions', 'hobbies', 'weather', 'making plans']},
        5: {'name': 'Shopping', 'topics': ['money', 'clothing', 'quantities', 'bargaining']},
        6: {'name': 'Dining', 'topics': ['restaurant', 'ordering food', 'preferences', 'recipes']},
        7: {'name': 'Travel', 'topics': ['hotel', 'airport', 'emergencies', 'reservations']},
        8: {'name': 'Work', 'topics': ['professions', 'office', 'schedules', 'meetings']},
        9: {'name': 'Culture', 'topics': ['traditions', 'media', 'opinions', 'current events']},
        10: {'name': 'Advanced', 'topics': ['abstract concepts', 'idioms', 'fluency', 'nuance']},
    }
    
    def __init__(self):
        """Initialize the adaptive test service."""
        self.api_key = getattr(settings, 'OPENAI_API_KEY', os.environ.get('OPENAI_API_KEY'))
        self.use_ai = bool(self.api_key)
        
        if not self.use_ai:
            logger.warning(
                'OpenAI API key not configured. Tests will use template questions.'
            )
    
    def generate_adaptive_test(self, user: User, language: str, level: int) -> dict:
        """
        Generate a personalized 10-question test.
        
        Questions are distributed based on user's skill mastery:
        - 70% from weak skills (< 60% mastery)
        - 30% from strong skills (>= 60% mastery)
        
        Args:
            user: The user taking the test
            language: Target language
            level: Proficiency level (1-10)
            
        Returns:
            dict: Test data with questions
                  {
                      'test_id': str,
                      'language': str,
                      'level': int,
                      'questions': [
                          {
                              'id': int,
                              'skill': str,
                              'question': str,
                              'options': list,
                              'correct_index': int,
                          }
                      ],
                      'time_limit_minutes': int,
                  }
        """
        # Get user's skill mastery for this language
        skill_distribution = self._get_skill_distribution(user, language)
        
        # Calculate question counts per skill
        question_counts = self._calculate_question_distribution(skill_distribution)
        
        # Generate questions
        questions = self._generate_questions(
            language, level, question_counts, skill_distribution
        )
        
        # Remove any duplicate questions (by question text)
        seen_questions = set()
        unique_questions = []
        for q in questions:
            question_text = q.get('question', '').strip().lower()
            if question_text and question_text not in seen_questions:
                seen_questions.add(question_text)
                unique_questions.append(q)
        
        # If we lost questions due to duplicates, log a warning
        if len(unique_questions) < len(questions):
            logger.warning('Removed %d duplicate questions from test', len(questions) - len(unique_questions))
        
        questions = unique_questions
        
        # Shuffle questions to mix skills
        random.shuffle(questions)
        
        # Number questions
        for i, q in enumerate(questions):
            q['id'] = i + 1
        
        return {
            'test_id': f"{user.id}-{language}-{level}-{timezone.now().timestamp()}",
            'language': language,
            'level': level,
            'questions': questions,
            'time_limit_minutes': 15,
            'total_questions': len(questions),
        }
    
    def evaluate_test(self, user: User, module, answers: list) -> dict:
        """
        Evaluate test answers and handle level progression.
        
        Args:
            user: The user who took the test
            module: LearningModule instance
            answers: List of answer dicts [{'question_id': int, 'answer_index': int}, ...]
            
        Returns:
            dict: Evaluation results
                  {
                      'score': float,  # Percentage
                      'correct': int,
                      'total': int,
                      'passed': bool,
                      'new_level': int | None,
                      'can_retry_at': datetime | None,
                      'feedback': list,
                  }
        """
        from home.models import UserModuleProgress, UserSkillMastery
        
        # Get or create progress record
        progress, _ = UserModuleProgress.objects.get_or_create(
            user=user,
            module=module
        )
        
        # Score the test (in a real implementation, we'd verify against stored questions)
        correct_count = sum(1 for a in answers if a.get('is_correct', False))
        total = len(answers)
        score = (correct_count / total * 100) if total > 0 else 0
        
        # Update progress
        progress.test_attempts += 1
        progress.last_test_date = timezone.now()
        if score > progress.best_test_score:
            progress.best_test_score = score
        
        # Determine pass/fail
        passed = score >= self.PASSING_SCORE
        result = {
            'score': round(score, 1),
            'correct': correct_count,
            'total': total,
            'passed': passed,
            'new_level': None,
            'can_retry_at': None,
            'feedback': [],
        }
        
        if passed:
            # Handle level progression
            progression = self._handle_level_progression(user, module, progress)
            result['new_level'] = progression.get('new_level')
            result['feedback'].append(progression['message'])
            progress.is_module_complete = True
            progress.completed_at = timezone.now()
        else:
            # Calculate retry time
            retry_time = timezone.now() + timedelta(minutes=self.RETRY_COOLDOWN_MINUTES)
            result['can_retry_at'] = retry_time
            result['feedback'].append(
                f"You scored {score:.0f}%. You need {self.PASSING_SCORE}% to advance. "
                f"Review the lessons and try again in {self.RETRY_COOLDOWN_MINUTES} minutes."
            )
        
        progress.save()
        
        # Update skill mastery based on answers
        self._update_skill_mastery(user, module.language, answers)
        
        return result
    
    def can_take_test(self, user: User, module) -> dict:
        """
        Check if user can take the test for this module.
        
        Requirements:
        1. All 5 lessons must be completed
        2. If previously failed, 24-hour cooldown must have passed
        
        Args:
            user: The user
            module: LearningModule instance
            
        Returns:
            dict: {
                'can_take': bool,
                'reason': str | None,
                'retry_available_at': datetime | None,
            }
        """
        from home.models import UserModuleProgress
        
        progress = UserModuleProgress.objects.filter(
            user=user, module=module
        ).first()
        
        if not progress:
            return {
                'can_take': False,
                'reason': 'Complete all 5 lessons before taking the test.',
                'retry_available_at': None,
            }
        
        if not progress.all_lessons_completed():
            completed = len(progress.lessons_completed)
            return {
                'can_take': False,
                'reason': f'Complete all 5 lessons ({completed}/5 done) before taking the test.',
                'retry_available_at': None,
            }
        
        if progress.is_module_complete:
            return {
                'can_take': False,
                'reason': 'You have already passed this test.',
                'retry_available_at': None,
            }
        
        if not progress.can_retry_test():
            retry_at = progress.last_test_date + timedelta(minutes=self.RETRY_COOLDOWN_MINUTES)
            return {
                'can_take': False,
                'reason': 'Please wait before retrying the test.',
                'retry_available_at': retry_at,
            }
        
        return {
            'can_take': True,
            'reason': None,
            'retry_available_at': None,
        }
    
    def _get_skill_distribution(self, user: User, language: str) -> dict:
        """
        Get user's mastery distribution across skills.
        
        Returns:
            dict: {
                'weak': [('vocabulary', 45.0), ('grammar', 55.0)],
                'strong': [('conversation', 75.0), ('reading', 80.0), ('listening', 70.0)],
            }
        """
        from home.models import SkillCategory, UserSkillMastery
        
        # Get all skill categories
        skills = SkillCategory.objects.all()
        
        weak_skills = []
        strong_skills = []
        
        for skill in skills:
            mastery = UserSkillMastery.objects.filter(
                user=user,
                skill_category=skill,
                language=language
            ).first()
            
            mastery_pct = mastery.mastery_percentage if mastery else 50.0  # Default to 50%
            
            if mastery_pct < self.WEAK_SKILL_THRESHOLD:
                weak_skills.append((skill.name, mastery_pct))
            else:
                strong_skills.append((skill.name, mastery_pct))
        
        # If no weak skills, treat lowest strong skills as weak
        if not weak_skills and strong_skills:
            strong_skills.sort(key=lambda x: x[1])
            # Move the 2 lowest to weak
            weak_skills = strong_skills[:2]
            strong_skills = strong_skills[2:]
        
        # If no strong skills, treat highest weak skills as strong
        if not strong_skills and weak_skills:
            weak_skills.sort(key=lambda x: x[1], reverse=True)
            strong_skills = weak_skills[:2]
            weak_skills = weak_skills[2:]
        
        return {
            'weak': weak_skills,
            'strong': strong_skills,
        }
    
    def _calculate_question_distribution(self, skill_distribution: dict) -> dict:
        """
        Calculate how many questions per skill.
        
        Ensures all 5 skills (vocabulary, grammar, conversation, reading, listening) 
        are represented with at least 1 question each.
        
        Args:
            skill_distribution: Output from _get_skill_distribution
            
        Returns:
            dict: {skill_name: question_count}
        """
        from home.models import SkillCategory
        
        weak_skills = skill_distribution['weak']
        strong_skills = skill_distribution['strong']
        
        # Get all 5 skills to ensure coverage
        all_skills = list(SkillCategory.objects.all().values_list('name', flat=True))
        
        # Target counts
        weak_count = int(self.TEST_QUESTION_COUNT * self.WEAK_SKILL_RATIO)  # 7
        strong_count = self.TEST_QUESTION_COUNT - weak_count  # 3
        
        distribution = {}
        
        # First, ensure each skill gets at least 1 question (5 questions minimum)
        for skill in all_skills:
            distribution[skill] = 1
        
        remaining_questions = self.TEST_QUESTION_COUNT - 5  # 5 remaining after ensuring coverage
        
        # Distribute remaining questions based on weak/strong ratio
        remaining_weak = int(remaining_questions * self.WEAK_SKILL_RATIO)
        remaining_strong = remaining_questions - remaining_weak
        
        # Add to weak skills
        if weak_skills and remaining_weak > 0:
            per_weak = remaining_weak // len(weak_skills)
            remainder = remaining_weak % len(weak_skills)
            for i, (skill, _) in enumerate(weak_skills):
                distribution[skill] = distribution.get(skill, 0) + per_weak + (1 if i < remainder else 0)
        
        # Add to strong skills
        if strong_skills and remaining_strong > 0:
            per_strong = remaining_strong // len(strong_skills)
            remainder = remaining_strong % len(strong_skills)
            for i, (skill, _) in enumerate(strong_skills):
                distribution[skill] = distribution.get(skill, 0) + per_strong + (1 if i < remainder else 0)
        
        return distribution
    
    def _generate_questions(
        self,
        language: str,
        level: int,
        question_counts: dict,
        skill_distribution: dict
    ) -> list:
        """
        Generate test questions using AI or templates.
        
        Args:
            language: Target language
            level: Proficiency level
            question_counts: Questions per skill
            skill_distribution: Weak/strong skill info
            
        Returns:
            list: Question objects
        """
        questions = []
        
        for skill, count in question_counts.items():
            if count <= 0:
                continue
            
            if self.use_ai:
                skill_questions = self._generate_ai_questions(
                    language, level, skill, count
                )
            else:
                skill_questions = self._generate_template_questions(
                    language, level, skill, count
                )
            
            questions.extend(skill_questions)
        
        return questions
    
    def _load_level_fixture(self, language: str, level: int) -> Optional[Dict]:
        """
        Load the level fixture data for a specific language and level.
        
        Args:
            language: Target language
            level: Proficiency level
            
        Returns:
            dict: Fixture data or None if not found
        """
        try:
            # Validate level is within expected range
            if not isinstance(level, int) or level < 1 or level > 10:
                logger.warning('Invalid level: %s (must be 1-10)', level)
                return None
            
            # Construct base fixture root directory
            fixture_root = os.path.join(
                settings.BASE_DIR,
                'home',
                'fixtures',
                'curriculum',
            )
            
            # Normalize and get absolute paths for security
            fixture_root = os.path.abspath(os.path.normpath(fixture_root))
            
            # Strictly validate language input using regex (only allow alphanumeric and hyphens)
            language_dir = language.strip().lower()
            
            # Validate language directory name: only letters, numbers, and hyphens, 2-30 chars
            if not re.fullmatch(r'[a-z0-9-]{2,30}', language_dir):
                logger.warning('Invalid language directory name: %s (must be 2-30 chars, alphanumeric and hyphens only)', 
                             language_dir)
                return None
            
            # Construct fixture path
            fixture_path = os.path.join(
                fixture_root,
                language_dir,
                f'level_{level:02d}.json'
            )
            
            # Normalize and verify path is within fixture_root (prevent path traversal)
            normalized_path = os.path.abspath(os.path.normpath(fixture_path))
            
            # Ensure the normalized path is within the fixture root directory
            # Use os.path.commonpath for robust cross-platform path containment check
            try:
                common_path = os.path.commonpath([fixture_root, normalized_path])
                if common_path != fixture_root:
                    logger.warning('Potential path traversal attack blocked: %s (root: %s)', 
                                 normalized_path, fixture_root)
                    return None
            except ValueError:
                # commonpath raises ValueError if paths are on different drives (Windows)
                # In this case, check if normalized_path starts with fixture_root
                if not normalized_path.startswith(fixture_root + os.sep):
                    logger.warning('Potential path traversal attack blocked: %s (root: %s)', 
                                 normalized_path, fixture_root)
                    return None
            
            if not os.path.exists(normalized_path):
                logger.warning('Fixture not found: %s', normalized_path)
                return None
            
            with open(normalized_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error('Failed to load fixture for %s level %d: %s', language, level, str(e))
            return None
    
    def _extract_lesson_content(self, fixture: Dict, skill: str) -> Dict:
        """
        Extract relevant lesson content for a specific skill from fixture data.
        
        Args:
            fixture: Complete fixture data
            skill: Skill category to extract
            
        Returns:
            dict: Extracted content for the skill
        """
        if not fixture or 'lessons' not in fixture:
            return {}
        
        # Find the lesson for this skill
        lesson = None
        for l in fixture.get('lessons', []):
            if l.get('skill', '').lower() == skill.lower():
                lesson = l
                break
        
        if not lesson:
            return {}
        
        # Extract relevant content based on skill type
        content = {
            'title': lesson.get('title', ''),
            'description': lesson.get('description', ''),
            'flashcards': lesson.get('flashcards', []),
            'quiz_questions': lesson.get('quiz_questions', []),
        }
        
        # For vocabulary: extract all vocabulary words
        if skill.lower() == 'vocabulary':
            vocab_words = []
            for card in content.get('flashcards', []):
                vocab_words.append({
                    'english': card.get('front', ''),
                    'target_language': card.get('back', '')
                })
            content['vocabulary_words'] = vocab_words
        
        # For grammar: extract grammar concepts from flashcards
        elif skill.lower() == 'grammar':
            grammar_concepts = []
            for card in content.get('flashcards', []):
                grammar_concepts.append({
                    'concept': card.get('front', ''),
                    'example': card.get('back', '')
                })
            content['grammar_concepts'] = grammar_concepts
        
        # For conversation: extract phrases and scenarios
        elif skill.lower() == 'conversation':
            phrases = []
            for card in content.get('flashcards', []):
                phrases.append({
                    'english': card.get('front', ''),
                    'target_language': card.get('back', '')
                })
            content['phrases'] = phrases
        
        return content
    
    def _build_lesson_context_prompt(self, lesson_content: Dict, skill: str) -> str:
        """
        Build a detailed context prompt section from lesson content.
        
        Args:
            lesson_content: Extracted lesson content
            skill: Skill category
            
        Returns:
            str: Formatted context section for the prompt
        """
        if not lesson_content:
            return ""
        
        context_parts = []
        
        # Add lesson title and description
        if lesson_content.get('title'):
            context_parts.append(f"Lesson Title: {lesson_content['title']}")
        if lesson_content.get('description'):
            context_parts.append(f"Lesson Description: {lesson_content['description']}")
        
        context_parts.append("")  # Blank line
        
        # Add skill-specific content
        if skill.lower() == 'vocabulary':
            vocab_words = lesson_content.get('vocabulary_words', [])
            if vocab_words:
                context_parts.append("VOCABULARY WORDS TAUGHT IN THIS LESSON:")
                for word in vocab_words[:20]:  # Limit to avoid token overflow
                    context_parts.append(f"  - {word['english']} = {word['target_language']}")
                context_parts.append("")
                context_parts.append("IMPORTANT: Generate questions that test understanding of these specific words:")
                context_parts.append("- Word meanings and translations")
                context_parts.append("- Usage in context and sentences")
                context_parts.append("- Appropriate situations for each word")
                context_parts.append("- Distinguishing between similar words")
        
        elif skill.lower() == 'grammar':
            grammar_concepts = lesson_content.get('grammar_concepts', [])
            if grammar_concepts:
                context_parts.append("GRAMMAR CONCEPTS TAUGHT IN THIS LESSON:")
                for concept in grammar_concepts[:15]:  # Limit to avoid token overflow
                    context_parts.append(f"  - {concept['concept']} → {concept['example']}")
                context_parts.append("")
                context_parts.append("IMPORTANT: Generate questions that test understanding of these specific grammar rules:")
                context_parts.append("- Correct application of these rules")
                context_parts.append("- Identifying correct vs incorrect usage")
                context_parts.append("- Sentence construction using these concepts")
        
        elif skill.lower() == 'conversation':
            phrases = lesson_content.get('phrases', [])
            if phrases:
                context_parts.append("CONVERSATION PHRASES TAUGHT IN THIS LESSON:")
                for phrase in phrases[:15]:  # Limit to avoid token overflow
                    context_parts.append(f"  - {phrase['english']} = {phrase['target_language']}")
                context_parts.append("")
                context_parts.append("IMPORTANT: Generate questions that test understanding of these phrases:")
                context_parts.append("- When to use each phrase")
                context_parts.append("- Appropriate responses in conversations")
                context_parts.append("- Social context and formality levels")
        
        elif skill.lower() == 'reading':
            # Use flashcards and quiz questions as context
            flashcards = lesson_content.get('flashcards', [])
            if flashcards:
                context_parts.append("READING CONTENT FROM THIS LESSON:")
                for card in flashcards[:10]:
                    context_parts.append(f"  - {card.get('front', '')} / {card.get('back', '')}")
                context_parts.append("")
                context_parts.append("IMPORTANT: Generate questions that test reading comprehension:")
                context_parts.append("- Understanding of simple texts and sentences")
                context_parts.append("- Identifying key information")
                context_parts.append("- Interpreting meaning from context")
        
        elif skill.lower() == 'listening':
            flashcards = lesson_content.get('flashcards', [])
            if flashcards:
                context_parts.append("LISTENING CONTENT FROM THIS LESSON:")
                for card in flashcards[:10]:
                    context_parts.append(f"  - {card.get('front', '')} / {card.get('back', '')}")
                context_parts.append("")
                context_parts.append("IMPORTANT: Generate questions that test listening comprehension:")
                context_parts.append("- Recognizing pronunciation and sounds")
                context_parts.append("- Understanding spoken words and phrases")
                context_parts.append("- Distinguishing between similar sounds")
        
        return "\n".join(context_parts)
    
    def _generate_ai_questions(
        self,
        language: str,
        level: int,
        skill: str,
        count: int
    ) -> list:
        """
        Generate questions using OpenAI with lesson-specific context.
        
        Args:
            language: Target language
            level: Proficiency level
            skill: Skill category
            count: Number of questions to generate
            
        Returns:
            list: Generated questions
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            theme = self.LEVEL_THEMES.get(level, self.LEVEL_THEMES[1])
            
            # Load fixture data for this level
            fixture = self._load_level_fixture(language, level)
            lesson_content = self._extract_lesson_content(fixture, skill) if fixture else {}
            lesson_context = self._build_lesson_context_prompt(lesson_content, skill)
            
            # Build the enhanced prompt
            prompt_parts = [
                f"Generate {count} multiple-choice questions for a {language} language test.",
                "",
                f"Level: {level}/10 ({theme['name']})",
                f"Skill Focus: {skill}",
                f"Theme Topics: {', '.join(theme['topics'])}",
                ""
            ]
            
            # Add lesson-specific context if available
            if lesson_context:
                prompt_parts.append("=" * 60)
                prompt_parts.append("LESSON CONTENT - USE THIS AS THE BASIS FOR YOUR QUESTIONS:")
                prompt_parts.append("=" * 60)
                prompt_parts.append(lesson_context)
                prompt_parts.append("")
                prompt_parts.append("CRITICAL: Your questions MUST be based on the specific content listed above.")
                prompt_parts.append("Do NOT generate generic questions. Test the actual material taught in this lesson.")
                prompt_parts.append("")
            else:
                prompt_parts.append("NOTE: Lesson content not available. Generate appropriate questions for this level.")
                prompt_parts.append("")
            
            prompt_parts.extend([
                "=" * 60,
                "QUESTION REQUIREMENTS:",
                "=" * 60,
                "",
                "CRITICAL REQUIREMENTS:",
                f"- Questions MUST test {skill} knowledge at level {level}",
                "- Each question must have exactly 4 options",
                "- Only one correct answer per question (correct_index: 0-3)",
                "- Include a brief explanation for the correct answer",
                "- Questions should be appropriate for this proficiency level",
                "- All fields are required: question, options, correct_index, explanation, skill",
                "",
                "QUESTION DIVERSITY - AVOID REPETITION:",
                f"- Generate {count} UNIQUE questions that test DIFFERENT aspects of {skill}",
                "- Each question must test a different concept, word, rule, or scenario",
                "- DO NOT create variations of the same question",
                "- DO NOT ask the same thing in different words",
                "- Cover the full breadth of content from the lesson",
                "",
                "Question Type Guidelines:",
                "- For vocabulary: Mix word meanings, usage in context, synonyms/antonyms, collocations, and appropriate situations",
                "- For grammar: Cover different grammar rules, sentence structures, verb forms, and correct vs incorrect usage",
                "- For conversation: Include different conversation scenarios, common phrases, social contexts, and appropriate responses",
                "- For reading: Test comprehension of different text types, reading strategies, and extracting key information",
                "- For listening: Cover different listening contexts, pronunciation recognition, and comprehension skills",
                "",
                "Return as JSON object with \"questions\" key containing an array:",
                "{",
                "  \"questions\": [",
                "    {",
                f"      \"question\": \"Question text in English asking about {language}\",",
                "      \"options\": [\"Option A text\", \"Option B text\", \"Option C text\", \"Option D text\"],",
                "      \"correct_index\": 0,",
                "      \"explanation\": \"Brief explanation of why this is correct\",",
                f"      \"skill\": \"{skill}\"",
                "    }",
                "  ]",
                "}"
            ])
            
            prompt = "\n".join(prompt_parts)
            
            system_message = (
                f"You are an expert {language} language teacher creating comprehensive test questions. "
                "Your questions must be based on the specific lesson content provided. "
                "Each question must test a DIFFERENT concept - avoid repetition and variations of the same question. "
                "Always return valid JSON with exactly the structure requested."
            )
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.8,  # Slightly higher for more variety
            )
            
            result = json.loads(response.choices[0].message.content)
            questions = result.get('questions', []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
            
            # Validate and clean questions
            validated_questions = []
            for q in questions[:count]:
                if not isinstance(q, dict):
                    logger.warning('Invalid question format (not a dict): %s', q)
                    continue
                    
                # Ensure all required fields exist
                if not all(key in q for key in ['question', 'options', 'correct_index']):
                    logger.warning('Question missing required fields: %s', q)
                    continue
                    
                # Ensure options is a list with at least 4 items
                if not isinstance(q.get('options'), list) or len(q.get('options', [])) < 4:
                    logger.warning('Question has invalid options: %s', q.get('options'))
                    continue
                    
                # Ensure correct_index is valid
                correct_idx = q.get('correct_index')
                if not isinstance(correct_idx, int) or correct_idx < 0 or correct_idx >= len(q.get('options', [])):
                    logger.warning('Question has invalid correct_index: %s', correct_idx)
                    continue
                
                # Ensure question text is not empty
                if not q.get('question') or not q.get('question').strip():
                    logger.warning('Question has empty question text')
                    continue
                
                # Set default values for optional fields
                q.setdefault('explanation', 'No explanation provided.')
                q.setdefault('skill', skill)
                
                validated_questions.append(q)
            
            if len(validated_questions) < count:
                logger.warning('Only %d/%d questions passed validation, using template fallback', 
                             len(validated_questions), count)
                # Fill remaining with templates if needed
                remaining = count - len(validated_questions)
                validated_questions.extend(
                    self._generate_template_questions(language, level, skill, remaining)
                )
            
            logger.info('Generated %d validated AI questions for %s %s level %d',
                       len(validated_questions), language, skill, level)
            
            return validated_questions[:count]
            
        except Exception as e:
            logger.error('AI question generation failed: %s', str(e))
            return self._generate_template_questions(language, level, skill, count)
    
    def _generate_template_questions(
        self,
        language: str,
        level: int,
        skill: str,
        count: int
    ) -> list:
        """
        Generate questions from templates (fallback when AI unavailable).
        
        Args:
            language: Target language
            level: Proficiency level
            skill: Skill category
            count: Number of questions
            
        Returns:
            list: Template-based questions
        """
        templates = {
            'vocabulary': [
                {
                    'question': f'What is the {language} word for "hello"?',
                    'options': ['Option A', 'Option B', 'Option C', 'Option D'],
                    'correct_index': 0,
                    'explanation': 'This is the standard greeting.',
                    'skill': 'vocabulary',
                },
            ],
            'grammar': [
                {
                    'question': f'Which is the correct verb conjugation in {language}?',
                    'options': ['Option A', 'Option B', 'Option C', 'Option D'],
                    'correct_index': 1,
                    'explanation': 'This follows the regular conjugation pattern.',
                    'skill': 'grammar',
                },
            ],
            'conversation': [
                {
                    'question': f'What would you say in {language} when meeting someone?',
                    'options': ['Option A', 'Option B', 'Option C', 'Option D'],
                    'correct_index': 0,
                    'explanation': 'This is the polite way to greet someone.',
                    'skill': 'conversation',
                },
            ],
            'reading': [
                {
                    'question': f'Based on the {language} text, what is the main idea?',
                    'options': ['Option A', 'Option B', 'Option C', 'Option D'],
                    'correct_index': 2,
                    'explanation': 'The text discusses this topic.',
                    'skill': 'reading',
                },
            ],
            'listening': [
                {
                    'question': f'What did the speaker say in {language}?',
                    'options': ['Option A', 'Option B', 'Option C', 'Option D'],
                    'correct_index': 1,
                    'explanation': 'The speaker mentioned this.',
                    'skill': 'listening',
                },
            ],
        }
        
        skill_templates = templates.get(skill, templates['vocabulary'])
        questions = []
        
        for i in range(count):
            template = skill_templates[i % len(skill_templates)].copy()
            template['question'] = f"Level {level} - {template['question']}"
            questions.append(template)
        
        return questions
    
    def _handle_level_progression(self, user: User, module, progress) -> dict:
        """
        Handle user advancement after passing a test.
        
        Args:
            user: The user
            module: Completed module
            progress: UserModuleProgress instance
            
        Returns:
            dict: Progression result
        """
        from home.models import UserLanguageProfile
        
        current_level = module.proficiency_level
        
        # Update user's language profile
        lang_profile, _ = UserLanguageProfile.objects.get_or_create(
            user=user,
            language=module.language
        )
        
        if current_level >= self.MAX_LEVEL:
            # At max level, loop back for continued practice
            return {
                'new_level': self.MAX_LEVEL,
                'message': (
                    f"🎉 Congratulations! You've mastered Level {self.MAX_LEVEL}! "
                    "You're now at advanced proficiency. Continue practicing to maintain your skills."
                ),
            }
        
        # Advance to next level
        new_level = current_level + 1
        lang_profile.proficiency_level = new_level
        lang_profile.save(update_fields=['proficiency_level'])
        
        # Also update main profile if this is their target language
        if hasattr(user, 'profile') and user.profile.target_language == module.language:
            user.profile.proficiency_level = new_level
            user.profile.save(update_fields=['proficiency_level'])
        
        return {
            'new_level': new_level,
            'message': (
                f"🎉 Excellent! You've advanced to Level {new_level}! "
                f"New lessons are now available."
            ),
        }
    
    def _update_skill_mastery(self, user: User, language: str, answers: list):
        """
        Update user's skill mastery based on test answers.
        
        Args:
            user: The user
            language: Target language
            answers: List of answer results with skill info
        """
        from home.models import SkillCategory, UserSkillMastery
        
        # Group answers by skill
        skill_results = {}
        for answer in answers:
            skill_name = answer.get('skill')
            if not skill_name:
                continue
            
            if skill_name not in skill_results:
                skill_results[skill_name] = {'correct': 0, 'total': 0}
            
            skill_results[skill_name]['total'] += 1
            if answer.get('is_correct'):
                skill_results[skill_name]['correct'] += 1
        
        # Update mastery for each skill
        for skill_name, results in skill_results.items():
            try:
                skill = SkillCategory.objects.get(name=skill_name)
                mastery, _ = UserSkillMastery.objects.get_or_create(
                    user=user,
                    skill_category=skill,
                    language=language
                )
                
                # Update with weighted average (recent results matter more)
                new_accuracy = (results['correct'] / results['total']) * 100
                # Blend: 70% old mastery, 30% new result
                mastery.mastery_percentage = (
                    mastery.mastery_percentage * 0.7 + new_accuracy * 0.3
                )
                mastery.total_attempts += results['total']
                mastery.correct_attempts += results['correct']
                mastery.last_practiced = timezone.now()
                mastery.save()
                
            except SkillCategory.DoesNotExist:
                logger.warning('Unknown skill category: %s', skill_name)

