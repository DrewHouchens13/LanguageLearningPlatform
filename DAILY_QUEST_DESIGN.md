# Daily Quest System Design

**Feature**: Daily Quests (Issue #18)
**Created**: November 13, 2025
**Status**: Design Phase

---

## Database Schema

### Model 1: DailyQuest
**Purpose**: Represents one daily quest available to all users for a specific date

```python
class DailyQuest(models.Model):
    """
    A daily quest generated from an existing lesson.
    One quest per day, available to all users.
    """
    # Identification
    date = models.DateField(unique=True, db_index=True)
    title = models.CharField(max_length=200)  # e.g., "Daily Colors Challenge"
    description = models.TextField()

    # Source and Configuration
    based_on_lesson = models.ForeignKey('Lesson', on_delete=models.CASCADE)
    quest_type = models.CharField(max_length=20)  # 'flashcard', 'quiz'

    # Rewards
    xp_reward = models.IntegerField()  # Calculated: lesson.xp_value * 0.75

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"Daily Quest - {self.date} - {self.title}"
```

---

### Model 2: DailyQuestQuestion
**Purpose**: Individual questions within a daily quest (5 max)

```python
class DailyQuestQuestion(models.Model):
    """
    A single question in a daily quest.
    Format depends on quest_type (flashcard vs quiz).
    """
    # Relationship
    daily_quest = models.ForeignKey(
        'DailyQuest',
        on_delete=models.CASCADE,
        related_name='questions'
    )

    # Question Content
    question_text = models.TextField()

    # For flashcard type
    answer_text = models.CharField(max_length=200, blank=True)

    # For quiz type
    options = models.JSONField(default=list, blank=True)  # ['option1', 'option2', ...]
    correct_index = models.IntegerField(null=True, blank=True)  # 0, 1, 2, 3

    # Ordering
    order = models.IntegerField()  # 1-5

    # Metadata
    difficulty_level = models.CharField(max_length=10, default='medium')

    class Meta:
        ordering = ['order']
        unique_together = [['daily_quest', 'order']]
        constraints = [
            models.CheckConstraint(
                check=models.Q(order__gte=1) & models.Q(order__lte=5),
                name='valid_question_order'
            )
        ]

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}"
```

---

### Model 3: UserDailyQuestAttempt
**Purpose**: Tracks user's progress and completion of daily quests

```python
class UserDailyQuestAttempt(models.Model):
    """
    Tracks a user's attempt at a daily quest.
    One attempt per user per quest (one per day).
    """
    # Relationships
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    daily_quest = models.ForeignKey(
        'DailyQuest',
        on_delete=models.CASCADE,
        related_name='attempts'
    )

    # Progress
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Results
    total_questions = models.IntegerField(default=5)
    correct_answers = models.IntegerField(default=0)

    # Rewards
    xp_earned = models.IntegerField(default=0)

    # State
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = [['user', 'daily_quest']]
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', '-started_at']),
            models.Index(fields=['daily_quest', 'is_completed']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.daily_quest.date} - {self.score}"

    @property
    def score(self):
        """Return score as 'X/5' format"""
        return f"{self.correct_answers}/{self.total_questions}"

    @property
    def score_percentage(self):
        """Return score as percentage"""
        if self.total_questions == 0:
            return 0
        return round((self.correct_answers / self.total_questions) * 100, 1)

    def calculate_xp(self):
        """Calculate XP based on correct answers"""
        if self.total_questions == 0:
            return 0
        max_xp = self.daily_quest.xp_reward
        return int((self.correct_answers / self.total_questions) * max_xp)
```

---

### Model 4: UserDailyQuestAnswer
**Purpose**: Stores individual answers for tracking/history

```python
class UserDailyQuestAnswer(models.Model):
    """
    Records a user's answer to a specific quest question.
    Used for detailed history and analytics.
    """
    # Relationships
    attempt = models.ForeignKey(
        'UserDailyQuestAttempt',
        on_delete=models.CASCADE,
        related_name='answers'
    )
    question = models.ForeignKey(
        'DailyQuestQuestion',
        on_delete=models.CASCADE
    )

    # Answer
    user_answer = models.TextField()
    is_correct = models.BooleanField()

    # Timing
    answered_at = models.DateTimeField(auto_now_add=True)
    time_taken_seconds = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['question__order']
        unique_together = [['attempt', 'question']]

    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} Q{self.question.order}: {self.user_answer}"
```

---

## Business Logic

### Quest Generation Service

```python
class DailyQuestService:
    """Service for generating and managing daily quests"""

    @staticmethod
    def generate_quest_for_date(date):
        """
        Generate a daily quest for the specified date.
        Returns existing quest if already generated.
        """
        # Check if quest already exists
        existing = DailyQuest.objects.filter(date=date).first()
        if existing:
            return existing

        # Select random lesson (weighted by lesson type)
        lesson = DailyQuestService._select_random_lesson()

        # Calculate XP (75% of lesson)
        xp_reward = int(lesson.xp_value * 0.75)

        # Create quest
        quest = DailyQuest.objects.create(
            date=date,
            title=f"Daily {lesson.title} Challenge",
            description=f"Test your {lesson.title} knowledge with harder questions!",
            based_on_lesson=lesson,
            quest_type=lesson.lesson_type,
            xp_reward=xp_reward
        )

        # Generate 5 harder questions
        DailyQuestService._generate_questions(quest, lesson)

        return quest

    @staticmethod
    def _select_random_lesson():
        """Select a random published lesson"""
        from home.models import Lesson
        import random

        lessons = list(Lesson.objects.filter(is_published=True))
        if not lessons:
            raise ValueError("No published lessons available")

        return random.choice(lessons)

    @staticmethod
    def _generate_questions(quest, lesson):
        """
        Generate 5 harder questions based on lesson content.
        Combines multiple concepts from the lesson.
        """
        if quest.quest_type == 'flashcard':
            DailyQuestService._generate_flashcard_questions(quest, lesson)
        elif quest.quest_type == 'quiz':
            DailyQuestService._generate_quiz_questions(quest, lesson)

    @staticmethod
    def _generate_flashcard_questions(quest, lesson):
        """Generate harder flashcard questions"""
        # Get all flashcards from lesson
        cards = list(lesson.cards.all())

        if len(cards) < 3:
            raise ValueError(f"Lesson {lesson.title} needs at least 3 flashcards")

        import random

        # Question 1-3: Individual cards (shuffle)
        selected_cards = random.sample(cards, min(3, len(cards)))
        for idx, card in enumerate(selected_cards, 1):
            DailyQuestQuestion.objects.create(
                daily_quest=quest,
                question_text=card.front_text,
                answer_text=card.back_text,
                order=idx
            )

        # Question 4-5: Combo questions (harder)
        if len(cards) >= 5:
            # Q4: Reverse question (answer -> front)
            reverse_card = random.choice(cards)
            DailyQuestQuestion.objects.create(
                daily_quest=quest,
                question_text=f"What word means '{reverse_card.back_text}'?",
                answer_text=reverse_card.front_text,
                order=4,
                difficulty_level='hard'
            )

            # Q5: Multiple items
            multi_cards = random.sample(cards, 3)
            question = "What are these three: " + ", ".join([c.front_text for c in multi_cards])
            answer = ", ".join([c.back_text for c in multi_cards])
            DailyQuestQuestion.objects.create(
                daily_quest=quest,
                question_text=question,
                answer_text=answer,
                order=5,
                difficulty_level='hard'
            )

    @staticmethod
    def _generate_quiz_questions(quest, lesson):
        """Generate harder quiz questions"""
        # Get all quiz questions from lesson
        quiz_questions = list(lesson.quiz_questions.all())

        if len(quiz_questions) < 5:
            raise ValueError(f"Lesson {lesson.title} needs at least 5 quiz questions")

        import random

        # Select 5 random questions
        selected = random.sample(quiz_questions, 5)

        for idx, q in enumerate(selected, 1):
            # Shuffle options to make harder
            options = q.options.copy()
            correct_answer = options[q.correct_index]
            random.shuffle(options)
            new_correct_index = options.index(correct_answer)

            DailyQuestQuestion.objects.create(
                daily_quest=quest,
                question_text=q.question,
                options=options,
                correct_index=new_correct_index,
                order=idx
            )
```

---

## XP Calculation

### Formula:
```python
max_xp = lesson.xp_value * 0.75
earned_xp = max_xp * (correct_answers / total_questions)
```

### Examples:
- **Colors Lesson** (100 XP)
  - Quest XP: 75
  - 5/5 correct → 75 XP
  - 4/5 correct → 60 XP
  - 3/5 correct → 45 XP

- **Numbers Lesson** (150 XP)
  - Quest XP: 112 (rounded from 112.5)
  - 5/5 correct → 112 XP
  - 4/5 correct → 89 XP
  - 3/5 correct → 67 XP

---

## URL Routes

```python
# urls.py
urlpatterns = [
    path('quests/daily/', views.daily_quest_view, name='daily_quest'),
    path('quests/daily/start/', views.start_daily_quest, name='start_daily_quest'),
    path('quests/daily/submit/', views.submit_daily_quest, name='submit_daily_quest'),
    path('quests/history/', views.quest_history, name='quest_history'),
]
```

---

## Views Structure

### 1. `daily_quest_view`
- Shows today's quest
- If completed: show results
- If not completed: show "Start Quest" button
- Requires authentication

### 2. `start_daily_quest`
- Creates UserDailyQuestAttempt
- Redirects to quest interface
- POST only

### 3. `submit_daily_quest`
- Validates answers
- Calculates score and XP
- Awards XP to user
- Marks quest as completed
- POST only (AJAX)

### 4. `quest_history`
- Shows all completed quests
- Total XP earned from quests
- Requires authentication

---

## Scheduled Tasks

### Daily Quest Generation (Celery/Cron)

```python
# Option 1: Generate at midnight UTC
from django.core.management.base import BaseCommand
from datetime import date

class Command(BaseCommand):
    help = 'Generate daily quest for today'

    def handle(self, *args, **options):
        today = date.today()
        quest = DailyQuestService.generate_quest_for_date(today)
        self.stdout.write(
            self.style.SUCCESS(f'Generated quest: {quest.title}')
        )
```

```bash
# Crontab entry (runs at midnight)
0 0 * * * cd /path/to/project && ./manage.py generate_daily_quest
```

### Option 2: Lazy Generation (On First Access)
- Generate quest when first user visits today
- Simpler, no cron job needed
- Slight delay on first visit

---

## Template Structure

### `daily_quest.html`
```django
{% extends "home/base.html" %}

{% block content %}
<div class="daily-quest-container">
    <h1>Daily Quest</h1>
    <p class="date">{{ quest.date|date:"F j, Y" }}</p>

    {% if attempt and attempt.is_completed %}
        <!-- Completed State -->
        <div class="quest-completed">
            <h2>✓ Quest Completed!</h2>
            <p class="score">{{ attempt.score }}</p>
            <p class="xp">+{{ attempt.xp_earned }} XP</p>
            <p>Come back tomorrow for a new quest!</p>
        </div>
    {% else %}
        <!-- Available State -->
        <div class="quest-info">
            <h2>{{ quest.title }}</h2>
            <p>{{ quest.description }}</p>
            <ul>
                <li>Questions: 5</li>
                <li>Reward: {{ quest.xp_reward }} XP</li>
                <li>Type: {{ quest.get_quest_type_display }}</li>
            </ul>
            <form method="post" action="{% url 'start_daily_quest' %}">
                {% csrf_token %}
                <button type="submit">Start Quest</button>
            </form>
        </div>
    {% endif %}
</div>
{% endblock %}
```

---

## Testing Strategy

### Unit Tests (TDD)
1. **Model Tests**
   - DailyQuest creation
   - Unique date constraint
   - XP calculation
   - Score properties

2. **Service Tests**
   - Quest generation
   - Question generation
   - Random lesson selection
   - Flashcard vs quiz logic

3. **View Tests**
   - Authentication required
   - One attempt per day
   - XP awarding
   - Completion tracking

### BDD Tests
- Run all scenarios in `features/daily_quests.feature`
- Verify end-to-end user flows
- Test with behave-django

---

## Migration Plan

### Phase 1: Models
```bash
python manage.py makemigrations
python manage.py migrate
```

### Phase 2: Admin Interface
- Register models in admin
- Test quest generation manually

### Phase 3: Views & Templates
- Implement views
- Create templates
- Test user flow

### Phase 4: Automated Generation
- Set up cron job or celery task
- Test daily generation

---

## Success Metrics

- [ ] All BDD scenarios passing
- [ ] 407+ unit tests passing
- [ ] 94%+ code coverage maintained
- [ ] Pylint score ≥9.0
- [ ] 0 security issues (Bandit)
- [ ] Quest generated daily automatically
- [ ] Users can complete quest once per day
- [ ] XP awarded correctly (75% of lesson)

---

**Status**: Ready for TDD Implementation
**Next Step**: Write failing tests, then implement models
