"""
Curriculum Generator Service for Language Learning Platform.

Generates localized curriculum content using OpenAI for translation and
cultural adaptation. Creates fixture files for all supported languages.

🤖 AI ASSISTANT: This service generates all 500 lessons across 10 languages.
- Uses English templates as base content
- Translates and culturally adapts via OpenAI
- Outputs JSON fixtures for seeding database

RELATED FILES:
- home/fixtures/curriculum/ - Output directory for fixtures
- home/management/commands/generate_curriculum.py - CLI interface
- home/management/commands/seed_curriculum.py - Loads fixtures to DB
"""

import json
import logging
import os
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class CurriculumGenerator:
    """
    Generate curriculum content using OpenAI for translation/localization.
    
    Usage:
        generator = CurriculumGenerator()
        
        # Generate a single level for one language
        generator.generate_level_content('Spanish', 2)
        
        # Generate all content for a language
        generator.generate_language('French')
        
        # Generate everything
        generator.generate_all_fixtures()
    """
    
    FIXTURES_DIR = 'home/fixtures/curriculum'
    
    # All supported languages
    SUPPORTED_LANGUAGES = [
        'Spanish', 'French', 'German', 'Italian', 'Portuguese',
        'Japanese', 'Korean', 'Chinese', 'Arabic', 'Russian'
    ]
    
    # Level themes and focus areas
    LEVEL_THEMES = {
        1: {
            'name': 'Basics',
            'description': 'Essential greetings, numbers 1-10, colors, and basic phrases.',
            'topics': ['greetings', 'numbers 1-10', 'colors', 'basic phrases', 'yes/no'],
        },
        2: {
            'name': 'Daily Life',
            'description': 'Family members, common foods, everyday objects, and time.',
            'topics': ['family', 'food', 'common objects', 'time', 'days of week'],
        },
        3: {
            'name': 'Getting Around',
            'description': 'Directions, transportation, places in the city, asking for help.',
            'topics': ['directions', 'transportation', 'places', 'asking for help', 'locations'],
        },
        4: {
            'name': 'Social',
            'description': 'Making introductions, hobbies, weather, and making plans.',
            'topics': ['introductions', 'hobbies', 'weather', 'making plans', 'feelings'],
        },
        5: {
            'name': 'Shopping',
            'description': 'Money, clothing, quantities, prices, and transactions.',
            'topics': ['money', 'clothing', 'quantities', 'prices', 'sizes'],
        },
        6: {
            'name': 'Dining',
            'description': 'Restaurant vocabulary, ordering food, preferences, and recipes.',
            'topics': ['restaurant', 'ordering', 'food preferences', 'recipes', 'cooking'],
        },
        7: {
            'name': 'Travel',
            'description': 'Hotels, airports, emergencies, reservations, and tourism.',
            'topics': ['hotel', 'airport', 'emergencies', 'reservations', 'sightseeing'],
        },
        8: {
            'name': 'Work',
            'description': 'Professions, office vocabulary, schedules, and meetings.',
            'topics': ['professions', 'office', 'schedules', 'meetings', 'communication'],
        },
        9: {
            'name': 'Culture',
            'description': 'Traditions, media, expressing opinions, and current events.',
            'topics': ['traditions', 'media', 'opinions', 'current events', 'arts'],
        },
        10: {
            'name': 'Advanced',
            'description': 'Abstract concepts, idioms, nuanced expression, and fluency.',
            'topics': ['abstract concepts', 'idioms', 'nuance', 'formal speech', 'advanced grammar'],
        },
    }
    
    # Content specifications per skill
    SKILL_SPECS = {
        'vocabulary': {'flashcards': 10, 'quiz_questions': 5},
        'grammar': {'flashcards': 5, 'quiz_questions': 8},
        'conversation': {'flashcards': 3, 'quiz_questions': 5},
        'reading': {'flashcards': 2, 'quiz_questions': 5},
        'listening': {'flashcards': 5, 'quiz_questions': 5},
    }
    
    def __init__(self):
        """Initialize the curriculum generator."""
        self.api_key = getattr(settings, 'OPENAI_API_KEY', os.environ.get('OPENAI_API_KEY'))
        
        if not self.api_key:
            raise ValueError(
                'OpenAI API key required for curriculum generation. '
                'Set OPENAI_API_KEY environment variable.'
            )
    
    def generate_level_content(self, language: str, level: int, dry_run: bool = False) -> dict:
        """
        Generate all 5 lessons for a language/level combination.
        
        Args:
            language: Target language (e.g., 'Spanish', 'French')
            level: Proficiency level (1-10)
            dry_run: If True, don't save to file
            
        Returns:
            dict: Complete fixture data
        """
        language = language.strip().title()
        
        if language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f'Unsupported language: {language}')
        
        if not 1 <= level <= 10:
            raise ValueError(f'Level must be 1-10, got: {level}')
        
        theme = self.LEVEL_THEMES[level]
        
        logger.info('Generating %s Level %d: %s', language, level, theme['name'])
        
        # Generate fixture structure
        fixture = {
            'meta': {
                'language': language,
                'level': level,
                'theme': theme['name'],
                'description': self._localize_description(theme['description'], language, level),
            },
            'module': {
                'name': theme['name'],
                'description': self._localize_description(theme['description'], language, level),
                'passing_score': 85,
            },
            'lessons': []
        }
        
        # Generate each skill lesson
        skills = ['vocabulary', 'grammar', 'conversation', 'reading', 'listening']
        for order, skill in enumerate(skills, 1):
            lesson = self._generate_lesson(language, level, skill, order, theme)
            fixture['lessons'].append(lesson)
        
        # Save to file
        if not dry_run:
            self._save_fixture(language, level, fixture)
        
        return fixture
    
    def generate_language(self, language: str, dry_run: bool = False):
        """Generate all 10 levels for a language."""
        for level in range(1, 11):
            self.generate_level_content(language, level, dry_run)
    
    def generate_all_fixtures(self, dry_run: bool = False):
        """Generate all 100 fixture files."""
        for language in self.SUPPORTED_LANGUAGES:
            self.generate_language(language, dry_run)
    
    def _generate_lesson(
        self,
        language: str,
        level: int,
        skill: str,
        order: int,
        theme: dict
    ) -> dict:
        """Generate a single lesson with flashcards and quiz questions."""
        specs = self.SKILL_SPECS[skill]
        
        # Generate lesson content via OpenAI
        content = self._generate_ai_content(language, level, skill, theme, specs)
        
        return {
            'skill': skill,
            'title': content['title'],
            'description': content['description'],
            'order': order,
            'flashcards': content['flashcards'],
            'quiz_questions': content['quiz_questions'],
        }
    
    def _generate_ai_content(
        self,
        language: str,
        level: int,
        skill: str,
        theme: dict,
        specs: dict
    ) -> dict:
        """Generate lesson content using OpenAI."""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            
            prompt = self._build_generation_prompt(
                language, level, skill, theme, specs
            )
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are an expert {language} language curriculum designer. "
                            "Create engaging, accurate educational content for language learners. "
                            "Always output valid JSON matching the exact structure requested."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=4000,
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info('Generated %s %s content for %s Level %d',
                       skill, language, theme['name'], level)
            return result
            
        except Exception as e:
            logger.error('AI content generation failed: %s', str(e))
            raise
    
    def _build_generation_prompt(
        self,
        language: str,
        level: int,
        skill: str,
        theme: dict,
        specs: dict
    ) -> str:
        """Build the prompt for content generation."""
        
        skill_descriptions = {
            'vocabulary': f"""
Create a vocabulary lesson teaching essential {language} words for the theme "{theme['name']}".
Topics to cover: {', '.join(theme['topics'])}

Flashcards should have:
- "front": English word/phrase
- "back": {language} translation (with pronunciation hint for non-Latin scripts)
- "order": 1 to {specs['flashcards']}

Quiz questions should test recognition and recall of vocabulary words.""",

            'grammar': f"""
Create a grammar lesson teaching {language} grammar concepts appropriate for level {level}.
Focus on grammar structures used with topics: {', '.join(theme['topics'])}

Flashcards should explain grammar rules:
- "front": English description of grammar concept
- "back": {language} grammar rule/pattern with example
- "order": 1 to {specs['flashcards']}

Quiz questions should test understanding of grammar rules and correct usage.""",

            'conversation': f"""
Create a conversation lesson with common {language} dialogue phrases for "{theme['name']}".
Focus on practical phrases for: {', '.join(theme['topics'])}

Flashcards should be dialogue phrases:
- "front": English phrase (in conversation context)
- "back": {language} phrase with natural usage
- "order": 1 to {specs['flashcards']}

Quiz questions should test appropriate responses and dialogue understanding.""",

            'reading': f"""
Create a reading comprehension lesson with short {language} texts about "{theme['name']}".

Flashcards should be short reading passages:
- "front": Topic/context in English
- "back": Short {language} text (2-3 sentences, level-appropriate)
- "order": 1 to {specs['flashcards']}

Quiz questions should test reading comprehension with passages provided in the question.""",

            'listening': f"""
Create a listening skills lesson for {language} focused on "{theme['name']}".

Flashcards should be audio-friendly phrases (TTS will read them):
- "front": English meaning
- "back": {language} phrase (clear pronunciation, appropriate for TTS)
- "order": 1 to {specs['flashcards']}

Quiz questions should test recognition of spoken words/phrases.
Questions should describe what was "heard" and test comprehension.""",
        }
        
        return f"""Generate a {skill} lesson for {language} learners.

Level: {level}/10 ({theme['name']})
Theme Description: {theme['description']}

{skill_descriptions[skill]}

IMPORTANT REQUIREMENTS:
1. All {language} text must be accurate and natural
2. Content difficulty must match level {level}/10
3. For non-Latin scripts ({language}), include romanization in parentheses
4. Quiz options must be plausible but only one correct
5. Explanations should be helpful and educational

Generate exactly {specs['flashcards']} flashcards and {specs['quiz_questions']} quiz questions.

Return JSON in this exact format:
{{
  "title": "Engaging lesson title in English",
  "description": "Brief description of what students will learn",
  "flashcards": [
    {{"front": "English text", "back": "{language} text", "order": 1}},
    ...
  ],
  "quiz_questions": [
    {{
      "question": "Question text in English about {language}",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 0,
      "explanation": "Why this answer is correct",
      "order": 1
    }},
    ...
  ]
}}"""
    
    def _localize_description(self, description: str, language: str, level: int) -> str:
        """Add language-specific context to description."""
        return f"{description} Start your {language} journey at Level {level}."
    
    def _save_fixture(self, language: str, level: int, data: dict):
        """Save fixture to JSON file."""
        # Create language directory
        lang_dir = os.path.join(self.FIXTURES_DIR, language.lower())
        os.makedirs(lang_dir, exist_ok=True)
        
        # Write fixture file
        filename = f'level_{level:02d}.json'
        filepath = os.path.join(lang_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info('Saved fixture: %s', filepath)
    
    def get_fixture_status(self) -> dict:
        """Check which fixtures exist."""
        status = {}
        
        for language in self.SUPPORTED_LANGUAGES:
            lang_lower = language.lower()
            lang_dir = os.path.join(self.FIXTURES_DIR, lang_lower)
            status[language] = {}
            
            for level in range(1, 11):
                filename = f'level_{level:02d}.json'
                filepath = os.path.join(lang_dir, filename)
                status[language][level] = os.path.exists(filepath)
        
        return status
    
    def get_missing_fixtures(self) -> list:
        """Get list of missing fixtures."""
        missing = []
        status = self.get_fixture_status()
        
        for language, levels in status.items():
            for level, exists in levels.items():
                if not exists:
                    missing.append((language, level))
        
        return missing

