"""
Management command to seed curriculum content from JSON fixtures.

Usage:
    # Seed a specific language and level
    python manage.py seed_curriculum --language Spanish --level 1
    
    # Seed all available fixtures
    python manage.py seed_curriculum --all
    
    # Preview what would be seeded (dry run)
    python manage.py seed_curriculum --language Spanish --level 1 --dry-run

🤖 AI ASSISTANT: This command loads curriculum fixtures into the database.
- Reads from home/fixtures/curriculum/<language>/level_XX.json
- Creates LearningModule, Lesson, Flashcard, LessonQuizQuestion records
- Idempotent: can be re-run without creating duplicates
"""

import json
import os

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from home.models import (
    Flashcard,
    LearningModule,
    Lesson,
    LessonQuizQuestion,
    SkillCategory,
)


class Command(BaseCommand):
    help = 'Seed curriculum content from JSON fixtures'
    
    FIXTURES_DIR = 'home/fixtures/curriculum'
    
    # Supported languages (matches fixture directory names)
    SUPPORTED_LANGUAGES = [
        'spanish', 'french', 'german', 'italian', 'portuguese',
        'japanese', 'korean', 'chinese', 'arabic', 'russian'
    ]
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--language',
            type=str,
            help='Language to seed (e.g., Spanish, French)'
        )
        parser.add_argument(
            '--level',
            type=int,
            help='Level to seed (1-10)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Seed all available fixtures'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be seeded without making changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-creation of existing content'
        )
    
    def handle(self, *args, **options):
        language = options.get('language')
        level = options.get('level')
        seed_all = options.get('all')
        dry_run = options.get('dry_run')
        force = options.get('force')
        
        if not seed_all and not (language and level):
            raise CommandError(
                'Please specify --language and --level, or use --all'
            )
        
        if seed_all:
            self._seed_all_fixtures(dry_run, force)
        else:
            self._seed_fixture(language, level, dry_run, force)
    
    def _seed_all_fixtures(self, dry_run: bool, force: bool):
        """Seed all available fixtures."""
        fixtures_found = 0
        
        for lang in self.SUPPORTED_LANGUAGES:
            lang_dir = os.path.join(self.FIXTURES_DIR, lang)
            if not os.path.exists(lang_dir):
                continue
            
            for filename in sorted(os.listdir(lang_dir)):
                if filename.startswith('level_') and filename.endswith('.json'):
                    # Extract level number from filename (e.g., level_01.json -> 1)
                    level_str = filename.replace('level_', '').replace('.json', '')
                    try:
                        level = int(level_str)
                        self._seed_fixture(lang.title(), level, dry_run, force)
                        fixtures_found += 1
                    except ValueError:
                        self.stderr.write(
                            self.style.WARNING(f'Skipping invalid filename: {filename}')
                        )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nProcessed {fixtures_found} fixture(s)')
        )
    
    def _seed_fixture(self, language: str, level: int, dry_run: bool, force: bool):
        """Seed a single fixture file."""
        # Normalize language name
        language_normalized = language.strip().title()
        language_dir = language.strip().lower()
        
        # Build fixture path
        fixture_path = os.path.join(
            self.FIXTURES_DIR,
            language_dir,
            f'level_{level:02d}.json'
        )
        
        if not os.path.exists(fixture_path):
            raise CommandError(f'Fixture not found: {fixture_path}')
        
        self.stdout.write(f'Loading fixture: {fixture_path}')
        
        # Load JSON data
        with open(fixture_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if dry_run:
            self._preview_fixture(data, language_normalized, level)
            return
        
        # Seed the data
        with transaction.atomic():
            self._create_module_and_lessons(data, language_normalized, level, force)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Seeded {language_normalized} Level {level}'
            )
        )
    
    def _preview_fixture(self, data: dict, language: str, level: int):
        """Preview what would be seeded."""
        self.stdout.write(self.style.WARNING('\n[DRY RUN] Would create:'))
        
        module = data.get('module', {})
        self.stdout.write(f'  Module: {language} Level {level} - {module.get("name", "Unnamed")}')
        
        lessons = data.get('lessons', [])
        for lesson in lessons:
            flashcard_count = len(lesson.get('flashcards', []))
            quiz_count = len(lesson.get('quiz_questions', []))
            self.stdout.write(
                f'    Lesson: {lesson.get("title", "Untitled")} '
                f'({lesson.get("skill", "?")})'
            )
            self.stdout.write(
                f'      - {flashcard_count} flashcards, {quiz_count} quiz questions'
            )
    
    def _create_module_and_lessons(
        self, data: dict, language: str, level: int, force: bool
    ):
        """Create database records from fixture data."""
        module_data = data.get('module', {})
        lessons_data = data.get('lessons', [])
        
        # Create or get the LearningModule
        module, created = LearningModule.objects.update_or_create(
            language=language,
            proficiency_level=level,
            defaults={
                'name': module_data.get('name', f'Level {level}'),
                'description': module_data.get('description', ''),
                'passing_score': module_data.get('passing_score', 85),
            }
        )
        
        if created:
            self.stdout.write(f'  Created module: {module}')
        else:
            self.stdout.write(f'  Updated module: {module}')
        
        # Process each lesson
        for lesson_data in lessons_data:
            self._create_lesson(module, language, level, lesson_data, force)
    
    def _create_lesson(
        self,
        module: LearningModule,
        language: str,
        level: int,
        lesson_data: dict,
        force: bool
    ):
        """Create a lesson with flashcards and quiz questions."""
        skill_name = lesson_data.get('skill', 'vocabulary')
        
        # Get skill category
        try:
            skill_category = SkillCategory.objects.get(name=skill_name)
        except SkillCategory.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(f'  Unknown skill: {skill_name}. Skipping lesson.')
            )
            return
        
        # Create unique slug for the lesson
        slug = f"{language.lower()}-level-{level}-{skill_name}"
        
        # Create or update the lesson
        lesson, created = Lesson.objects.update_or_create(
            slug=slug,
            defaults={
                'title': lesson_data.get('title', f'{skill_name.title()} Lesson'),
                'description': lesson_data.get('description', ''),
                'language': language,
                'difficulty_level': level,
                'skill_category': skill_category,
                'order': lesson_data.get('order', skill_category.order),
                'is_published': True,
                'category': skill_name.title(),
                'lesson_type': 'flashcard',
                'xp_value': 100,
            }
        )
        
        action = 'Created' if created else 'Updated'
        self.stdout.write(f'    {action} lesson: {lesson.title}')
        
        # Clear existing content if force flag is set
        if force and not created:
            lesson.cards.all().delete()
            lesson.quiz_questions.all().delete()
            self.stdout.write('      Cleared existing content')
        
        # Create flashcards
        flashcards = lesson_data.get('flashcards', [])
        for fc_data in flashcards:
            Flashcard.objects.get_or_create(
                lesson=lesson,
                front_text=fc_data.get('front', ''),
                defaults={
                    'back_text': fc_data.get('back', ''),
                    'order': fc_data.get('order', 0),
                    'image_url': fc_data.get('image_url', ''),
                    'audio_url': fc_data.get('audio_url', ''),
                }
            )
        self.stdout.write(f'      Added {len(flashcards)} flashcards')
        
        # Create quiz questions
        quiz_questions = lesson_data.get('quiz_questions', [])
        for q_data in quiz_questions:
            LessonQuizQuestion.objects.get_or_create(
                lesson=lesson,
                question=q_data.get('question', ''),
                defaults={
                    'options': q_data.get('options', []),
                    'correct_index': q_data.get('correct_index', 0),
                    'explanation': q_data.get('explanation', ''),
                    'order': q_data.get('order', 0),
                }
            )
        self.stdout.write(f'      Added {len(quiz_questions)} quiz questions')

