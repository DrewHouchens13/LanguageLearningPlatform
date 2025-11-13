"""
Service for generating and managing daily quests.
"""
import secrets
from home.models import Lesson, DailyQuest, DailyQuestQuestion

# Use secrets.SystemRandom() for cryptographically secure random selection
# Even though this is not security-critical (just quiz selection),
# using secrets is better practice and satisfies Bandit security scanner
_random = secrets.SystemRandom()


class DailyQuestService:
    """Service for generating and managing daily quests"""

    @staticmethod
    def generate_quest_for_date(quest_date):
        """
        Generate a daily quest for the specified date.
        Returns existing quest if already generated.

        Args:
            quest_date: date object for the quest

        Returns:
            DailyQuest instance
        """
        # Check if quest already exists
        existing = DailyQuest.objects.filter(date=quest_date).first()
        if existing:
            return existing

        # Select random lesson (weighted by lesson type)
        lesson = DailyQuestService._select_random_lesson()

        # Calculate XP (75% of lesson)
        xp_reward = int(lesson.xp_value * 0.75)

        # Create quest
        quest = DailyQuest.objects.create(
            date=quest_date,
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
        """
        Select a random published lesson.

        Returns:
            Lesson instance

        Raises:
            ValueError: If no published lessons available
        """
        lessons = list(Lesson.objects.filter(is_published=True))
        if not lessons:
            raise ValueError("No published lessons available")

        return _random.choice(lessons)

    @staticmethod
    def _generate_questions(quest, lesson):
        """
        Generate 5 harder questions based on lesson content.
        Combines multiple concepts from the lesson.

        Args:
            quest: DailyQuest instance
            lesson: Lesson instance
        """
        if quest.quest_type == 'flashcard':
            DailyQuestService._generate_flashcard_questions(quest, lesson)
        elif quest.quest_type == 'quiz':
            DailyQuestService._generate_quiz_questions(quest, lesson)

    @staticmethod
    def _generate_flashcard_questions(quest, lesson):
        """
        Generate harder flashcard questions.

        Args:
            quest: DailyQuest instance
            lesson: Lesson instance

        Raises:
            ValueError: If lesson has < 3 flashcards
        """
        # Get all flashcards from lesson
        cards = list(lesson.cards.all())

        if len(cards) < 3:
            raise ValueError(f"Lesson {lesson.title} needs at least 3 flashcards")

        # Question 1-3: Individual cards (shuffle)
        selected_cards = _random.sample(cards, min(3, len(cards)))
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
            reverse_card = _random.choice(cards)
            DailyQuestQuestion.objects.create(
                daily_quest=quest,
                question_text=f"What word means '{reverse_card.back_text}'?",
                answer_text=reverse_card.front_text,
                order=4,
                difficulty_level='hard'
            )

            # Q5: Multiple items
            multi_cards = _random.sample(cards, min(3, len(cards)))
            question = "What are these three: " + ", ".join([c.front_text for c in multi_cards])
            answer = ", ".join([c.back_text for c in multi_cards])
            DailyQuestQuestion.objects.create(
                daily_quest=quest,
                question_text=question,
                answer_text=answer,
                order=5,
                difficulty_level='hard'
            )
        else:
            # If < 5 cards, just use more individual cards
            remaining_cards = [c for c in cards if c not in selected_cards]
            for idx, card in enumerate(remaining_cards[:2], 4):
                DailyQuestQuestion.objects.create(
                    daily_quest=quest,
                    question_text=card.front_text,
                    answer_text=card.back_text,
                    order=idx
                )

    @staticmethod
    def _generate_quiz_questions(quest, lesson):
        """
        Generate harder quiz questions.

        Args:
            quest: DailyQuest instance
            lesson: Lesson instance

        Raises:
            ValueError: If lesson has < 5 quiz questions
        """
        # Get all quiz questions from lesson
        quiz_questions = list(lesson.quiz_questions.all())

        if len(quiz_questions) < 5:
            raise ValueError(f"Lesson {lesson.title} needs at least 5 quiz questions")

        # Select 5 random questions
        selected = _random.sample(quiz_questions, 5)

        for idx, question in enumerate(selected, 1):
            # Shuffle options to make harder
            options = question.options.copy()
            correct_answer = options[question.correct_index]
            _random.shuffle(options)
            new_correct_index = options.index(correct_answer)

            DailyQuestQuestion.objects.create(
                daily_quest=quest,
                question_text=question.question,
                options=options,
                correct_index=new_correct_index,
                order=idx
            )
