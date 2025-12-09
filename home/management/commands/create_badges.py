from django.core.management.base import BaseCommand
from home.models import Badge

class Command(BaseCommand):
    help = 'Create initial achievement badges'

    def handle(self, *args, **kwargs):
        badges = [
            {
                'name': 'First Steps',
                'badge_type': 'first_lesson',
                'description': 'Complete your first lesson',
                'icon': '🎯'
            },
            {
                'name': 'Perfect Score',
                'badge_type': 'perfect_score',
                'description': 'Get 100% on a quiz',
                'icon': '💯'
            },
            {
                'name': 'Dedicated Learner',
                'badge_type': 'five_lessons',
                'description': 'Complete 5 lessons',
                'icon': '📚'
            },
            {
                'name': 'Language Explorer',
                'badge_type': 'ten_lessons',
                'description': 'Complete 10 lessons',
                'icon': '🌍'
            },
            {
                'name': 'Quiz Master',
                'badge_type': 'quiz_master',
                'description': 'Get 5 perfect scores',
                'icon': '👑'
            },
        ]
        
        for badge_data in badges:
            badge, created = Badge.objects.get_or_create(
                badge_type=badge_data['badge_type'],
                defaults=badge_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created badge: {badge.name}'))
            else:
                self.stdout.write(f'Badge already exists: {badge.name}')
