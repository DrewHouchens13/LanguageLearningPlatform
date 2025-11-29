"""
Management command to generate curriculum content fixtures using OpenAI.

Usage:
    # Generate a specific language and level
    python manage.py generate_curriculum --language Spanish --level 2
    
    # Generate all levels for a language
    python manage.py generate_curriculum --language French
    
    # Generate all missing fixtures
    python manage.py generate_curriculum --all
    
    # Check fixture status
    python manage.py generate_curriculum --status
    
    # Preview without generating
    python manage.py generate_curriculum --language German --level 1 --dry-run

🤖 AI ASSISTANT: This command generates curriculum JSON fixtures.
- Uses OpenAI to create authentic, localized content
- Generates 5 lessons per level (vocab, grammar, conversation, reading, listening)
- Each lesson has flashcards and quiz questions per specs
- Output goes to home/fixtures/curriculum/<language>/level_XX.json
"""

import time

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Generate curriculum content fixtures using OpenAI'
    
    SUPPORTED_LANGUAGES = [
        'Spanish', 'French', 'German', 'Italian', 'Portuguese',
        'Japanese', 'Korean', 'Chinese', 'Arabic', 'Russian'
    ]
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--language',
            type=str,
            help='Language to generate (e.g., Spanish, French)'
        )
        parser.add_argument(
            '--level',
            type=int,
            help='Specific level to generate (1-10)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Generate all missing fixtures for all languages'
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show which fixtures exist/missing'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be generated without saving'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Delay between API calls in seconds (default: 2.0)'
        )
    
    def handle(self, *args, **options):
        from home.services.curriculum_generator import CurriculumGenerator
        
        language = options.get('language')
        level = options.get('level')
        generate_all = options.get('all')
        show_status = options.get('status')
        dry_run = options.get('dry_run')
        delay = options.get('delay')
        
        try:
            generator = CurriculumGenerator()
        except ValueError as e:
            raise CommandError(str(e))
        
        if show_status:
            self._show_status(generator)
            return
        
        if not generate_all and not language:
            raise CommandError(
                'Please specify --language, --all, or --status'
            )
        
        if generate_all:
            self._generate_all(generator, dry_run, delay)
        elif language and level:
            self._generate_single(generator, language, level, dry_run)
        elif language:
            self._generate_language(generator, language, dry_run, delay)
        else:
            raise CommandError(
                'Please specify --level with --language, or use --all'
            )
    
    def _show_status(self, generator):
        """Display fixture generation status."""
        status = generator.get_fixture_status()
        missing = generator.get_missing_fixtures()
        
        self.stdout.write('\n📊 Curriculum Fixture Status\n')
        self.stdout.write('=' * 60)
        
        for language in self.SUPPORTED_LANGUAGES:
            levels = status.get(language, {})
            existing = sum(1 for exists in levels.values() if exists)
            
            if existing == 10:
                emoji = '✅'
                style = self.style.SUCCESS
            elif existing > 0:
                emoji = '🔶'
                style = self.style.WARNING
            else:
                emoji = '❌'
                style = self.style.ERROR
            
            # Build level indicators
            level_str = ''
            for lvl in range(1, 11):
                if levels.get(lvl, False):
                    level_str += self.style.SUCCESS('●')
                else:
                    level_str += self.style.ERROR('○')
            
            self.stdout.write(
                f'{emoji} {language:12} [{level_str}] {existing}/10'
            )
        
        self.stdout.write('=' * 60)
        total_missing = len(missing)
        total_fixtures = 100
        total_existing = total_fixtures - total_missing
        
        self.stdout.write(
            f'\nTotal: {total_existing}/{total_fixtures} fixtures generated'
        )
        
        if missing:
            self.stdout.write(
                self.style.WARNING(f'\n{total_missing} fixtures remaining to generate')
            )
    
    def _generate_single(self, generator, language: str, level: int, dry_run: bool):
        """Generate a single level fixture."""
        language = language.strip().title()
        
        if language not in self.SUPPORTED_LANGUAGES:
            raise CommandError(
                f'Unsupported language: {language}. '
                f'Supported: {", ".join(self.SUPPORTED_LANGUAGES)}'
            )
        
        if not 1 <= level <= 10:
            raise CommandError('Level must be between 1 and 10')
        
        self.stdout.write(f'\n🔄 Generating {language} Level {level}...\n')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] Would generate:'))
            self._preview_generation(generator, language, level)
            return
        
        try:
            fixture = generator.generate_level_content(language, level)
            self._report_fixture(fixture)
            self.stdout.write(
                self.style.SUCCESS(f'\n✅ Generated {language} Level {level}')
            )
        except Exception as e:
            raise CommandError(f'Generation failed: {str(e)}')
    
    def _generate_language(self, generator, language: str, dry_run: bool, delay: float):
        """Generate all 10 levels for a language."""
        language = language.strip().title()
        
        if language not in self.SUPPORTED_LANGUAGES:
            raise CommandError(
                f'Unsupported language: {language}. '
                f'Supported: {", ".join(self.SUPPORTED_LANGUAGES)}'
            )
        
        self.stdout.write(f'\n🔄 Generating all 10 levels for {language}...\n')
        
        status = generator.get_fixture_status()
        lang_status = status.get(language, {})
        
        for level in range(1, 11):
            if lang_status.get(level, False):
                self.stdout.write(
                    f'  Level {level}: Already exists, skipping'
                )
                continue
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f'  [DRY RUN] Would generate Level {level}')
                )
                continue
            
            try:
                self.stdout.write(f'  Generating Level {level}...')
                generator.generate_level_content(language, level)
                self.stdout.write(
                    self.style.SUCCESS(f'  ✅ Level {level} complete')
                )
                
                # Rate limiting delay
                if level < 10:
                    time.sleep(delay)
                    
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f'  ❌ Level {level} failed: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ {language} generation complete')
        )
    
    def _generate_all(self, generator, dry_run: bool, delay: float):
        """Generate all missing fixtures."""
        missing = generator.get_missing_fixtures()
        
        if not missing:
            self.stdout.write(
                self.style.SUCCESS('\n✅ All fixtures already exist!')
            )
            return
        
        total = len(missing)
        self.stdout.write(f'\n🔄 Generating {total} missing fixtures...\n')
        
        completed = 0
        failed = 0
        
        for language, level in missing:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'  [DRY RUN] Would generate {language} Level {level}'
                    )
                )
                continue
            
            try:
                self.stdout.write(f'  [{completed + 1}/{total}] {language} Level {level}...')
                generator.generate_level_content(language, level)
                completed += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✅ {language} Level {level} complete')
                )
                
                # Rate limiting
                time.sleep(delay)
                
            except Exception as e:
                failed += 1
                self.stderr.write(
                    self.style.ERROR(
                        f'  ❌ {language} Level {level} failed: {str(e)}'
                    )
                )
        
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(
            self.style.SUCCESS(f'Completed: {completed}/{total}')
        )
        if failed:
            self.stdout.write(
                self.style.ERROR(f'Failed: {failed}/{total}')
            )
    
    def _preview_generation(self, generator, language: str, level: int):
        """Preview what would be generated."""
        theme = generator.LEVEL_THEMES[level]
        
        self.stdout.write(f'\nLanguage: {language}')
        self.stdout.write(f'Level: {level} - {theme["name"]}')
        self.stdout.write(f'Description: {theme["description"]}')
        self.stdout.write(f'Topics: {", ".join(theme["topics"])}')
        self.stdout.write('\nLessons to generate:')
        
        for skill, specs in generator.SKILL_SPECS.items():
            self.stdout.write(
                f'  • {skill.title()}: '
                f'{specs["flashcards"]} flashcards, '
                f'{specs["quiz_questions"]} quiz questions'
            )
        
        self.stdout.write(f'\nTotal: 25 flashcards, 28 quiz questions')
    
    def _report_fixture(self, fixture: dict):
        """Report details of generated fixture."""
        meta = fixture.get('meta', {})
        lessons = fixture.get('lessons', [])
        
        self.stdout.write(f'\n  Theme: {meta.get("theme", "Unknown")}')
        self.stdout.write(f'  Description: {meta.get("description", "")[:60]}...')
        self.stdout.write(f'\n  Lessons generated:')
        
        total_fc = 0
        total_qq = 0
        
        for lesson in lessons:
            fc_count = len(lesson.get('flashcards', []))
            qq_count = len(lesson.get('quiz_questions', []))
            total_fc += fc_count
            total_qq += qq_count
            
            self.stdout.write(
                f'    • {lesson["skill"].title()}: '
                f'{fc_count} flashcards, {qq_count} questions'
            )
        
        self.stdout.write(f'\n  Total: {total_fc} flashcards, {total_qq} quiz questions')

