from django.db import models, IntegrityError, DatabaseError, transaction
from django.db.models import Sum, Count
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import hashlib
import os
import logging

# Configure logger for error tracking
logger = logging.getLogger(__name__)


def user_avatar_path(instance, filename):
    """
    Generate upload path for user avatars.

    Args:
        instance: UserProfile instance
        filename: Original filename

    Returns:
        str: Upload path in format 'avatars/user_<id>/<filename>'
    """
    ext = os.path.splitext(filename)[1]
    new_filename = f"avatar{ext}"
    return os.path.join('avatars', f'user_{instance.user.id}', new_filename)


class UserProfile(models.Model):
    """
    Extended user profile with avatar support and language learning settings.

    Features:
    - Avatar: Gravatar as default (based on email) with optional custom upload
    - Proficiency: CEFR level tracking from onboarding assessment
    - Learning preferences: Target language, daily goals, motivation
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Avatar support
    avatar = models.ImageField(
        upload_to=user_avatar_path,
        blank=True,
        null=True,
        help_text="Profile picture (max 5MB, PNG/JPG only)"
    )

    # Proficiency tracking (capped at B1 for new users)
    proficiency_level = models.CharField(
        max_length=2,
        choices=[
            ('A1', 'Beginner (A1)'),
            ('A2', 'Elementary (A2)'),
            ('B1', 'Intermediate (B1)'),
        ],
        null=True,
        blank=True,
        help_text="CEFR proficiency level determined by onboarding assessment"
    )

    # Onboarding state
    has_completed_onboarding = models.BooleanField(default=False)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)

    # Learning preferences
    target_language = models.CharField(max_length=50, default='Spanish')
    daily_goal_minutes = models.IntegerField(default=15)
    learning_motivation = models.TextField(blank=True)

    # XP and Leveling System (Sprint 3 - Issue #17)
    total_xp = models.PositiveIntegerField(
        default=0,
        help_text="Total experience points earned from completing lessons and quests"
    )
    current_level = models.PositiveIntegerField(
        default=1,
        help_text="Current level based on total XP earned"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        level_display = self.get_proficiency_level_display() if self.proficiency_level else 'Not assessed'
        return f"{self.user.username}'s Profile - {level_display}"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def get_gravatar_url(self, size=200):
        """
        Get Gravatar URL for user's email.

        Args:
            size: Image size in pixels (default 200)

        Returns:
            str: Gravatar URL with default fallback
        """
        email = self.user.email.lower().encode('utf-8')
        email_hash = hashlib.md5(email, usedforsecurity=False).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?s={size}&d=identicon"

    def get_avatar_url(self):
        """
        Get avatar URL with fallback to Gravatar.

        Returns:
            str: URL to user's avatar (custom upload or Gravatar)
        """
        if self.avatar:
            return self.avatar.url
        return self.get_gravatar_url()

    def get_avatar_thumbnail_url(self):
        """
        Get small avatar URL for navigation bar (40x40).

        Returns:
            str: URL to thumbnail avatar
        """
        if self.avatar:
            return self.avatar.url
        return self.get_gravatar_url(size=40)

    def save(self, *args, **kwargs):
        """
        Override save to resize avatar images to 200x200 pixels.

        Automatically resizes uploaded avatars to a maximum of 200x200 pixels
        while maintaining aspect ratio. Images are saved in their original format
        (PNG or JPEG) with high quality.
        """
        if self.avatar:
            try:
                # Open and validate the uploaded image
                img = Image.open(self.avatar)

                # Verify it's a valid image by attempting to load it
                img.verify()

                # Re-open after verify (verify() closes the file)
                self.avatar.seek(0)
                img = Image.open(self.avatar)

                # Convert RGBA to RGB for JPEG compatibility
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background

                # Resize image if larger than 200x200
                max_size = (200, 200)
                if img.height > max_size[1] or img.width > max_size[0]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)

                # Save resized image to BytesIO
                output = BytesIO()
                img_format = 'JPEG' if self.avatar.name.lower().endswith('.jpg') or self.avatar.name.lower().endswith('.jpeg') else 'PNG'
                img.save(output, format=img_format, quality=95)
                output.seek(0)

                # Replace avatar with resized version
                self.avatar.save(
                    self.avatar.name,
                    ContentFile(output.read()),
                    save=False
                )
            except UnidentifiedImageError as e:
                # Handle unrecognized image formats (must be before OSError as it's a subclass)
                logger.error('Unidentified image format for user %s: %s', self.user.username, str(e))
                raise ValidationError('Unrecognized image format. Please upload a valid PNG or JPG image.') from e
            except (IOError, OSError) as e:
                # Handle corrupted or invalid image files
                logger.error('Failed to process avatar image for user %s: %s', self.user.username, str(e))
                raise ValidationError('Invalid or corrupted image file. Please upload a valid PNG or JPG image.') from e
            except ValueError as e:
                # Handle invalid parameter values during image processing
                logger.error('Invalid image parameters for user %s: %s', self.user.username, str(e))
                raise ValidationError('Invalid image data. Please upload a different PNG or JPG image.') from e

        super().save(*args, **kwargs)

    # XP and Leveling System Methods (Sprint 3 - Issue #17)

    @staticmethod
    def get_xp_for_level(level):
        """
        Calculate total XP required to reach a specific level.

        Uses a balanced progression formula: XP = 100 * (level - 1)^1.5
        This creates a smooth difficulty curve for leveling up.

        Args:
            level: Target level (1, 2, 3, etc.)

        Returns:
            int: Total XP required to reach that level

        Examples:
            Level 1: 0 XP
            Level 2: 100 XP
            Level 3: 282 XP
            Level 4: 519 XP
            Level 5: 800 XP
        """
        if level <= 1:
            return 0
        return int(100 * ((level - 1) ** 1.5))

    def calculate_level_from_xp(self):
        """
        Calculate current level based on total XP.

        Returns:
            int: Level based on total XP (minimum 1)
        """
        level = 1
        while self.total_xp >= self.get_xp_for_level(level + 1):
            level += 1
        return level

    def get_xp_to_next_level(self):
        """
        Calculate XP needed to reach next level.

        Returns:
            int: XP required for next level
        """
        next_level = self.current_level + 1
        xp_for_next_level = self.get_xp_for_level(next_level)
        return xp_for_next_level - self.total_xp

    def get_progress_to_next_level(self):
        """
        Calculate progress percentage to next level.

        Returns:
            float: Percentage (0-100) of progress to next level
        """
        current_level_xp = self.get_xp_for_level(self.current_level)
        next_level_xp = self.get_xp_for_level(self.current_level + 1)
        level_xp_range = next_level_xp - current_level_xp

        if level_xp_range == 0:
            return 100.0

        xp_in_current_level = self.total_xp - current_level_xp
        progress = (xp_in_current_level / level_xp_range) * 100
        return min(100.0, max(0.0, progress))

    @transaction.atomic
    def award_xp(self, amount):
        """
        Award XP to user and check for level up.
        Uses atomic transaction to ensure data integrity.

        Args:
            amount: XP to award (must be positive integer/float)

        Returns:
            dict: {
                'xp_awarded': int,
                'total_xp': int,
                'leveled_up': bool,
                'new_level': int or None,
                'old_level': int
            }

        Raises:
            TypeError: If amount is not a number
            ValueError: If amount is negative or unreasonably large
            DatabaseError: If database save operation fails
        """
        # Type validation
        if not isinstance(amount, (int, float)):
            raise TypeError(f"XP amount must be numeric, got {type(amount).__name__}")

        # Convert to int for consistency
        amount = int(amount)

        # Range validation
        if amount < 0:
            raise ValueError(f"XP amount must be non-negative, got {amount}")

        if amount > 100000:  # Sanity check: prevent abuse with unreasonable values
            raise ValueError(f"XP amount {amount} exceeds maximum allowed (100000)")

        # Zero XP is valid but no-op
        if amount == 0:
            logger.debug('Zero XP award attempted for user %s', self.user.username)
            return {
                'xp_awarded': 0,
                'total_xp': self.total_xp,
                'leveled_up': False,
                'new_level': None,
                'old_level': self.current_level
            }

        # Overflow protection: Check if adding amount would exceed max PositiveIntegerField
        max_positive_int = 2147483647  # 2^31 - 1
        if self.total_xp + amount > max_positive_int:
            raise ValueError(
                f"XP overflow: {self.total_xp} + {amount} = {self.total_xp + amount} "
                f"exceeds maximum ({max_positive_int})"
            )

        # Use atomic transaction to ensure data integrity
        try:
            with transaction.atomic():
                old_level = self.current_level
                old_xp = self.total_xp
                self.total_xp += amount

                # Recalculate level based on new XP
                new_level = self.calculate_level_from_xp()
                leveled_up = new_level > old_level

                if leveled_up:
                    self.current_level = new_level
                    # Save both fields if level changed
                    self.save(update_fields=['total_xp', 'current_level'])
                    logger.info('User %s leveled up! %d → %d (awarded %d XP, total %d)',
                               self.user.username, old_level, new_level, amount, self.total_xp)
                else:
                    # Only save XP if no level change (performance optimization)
                    self.save(update_fields=['total_xp'])
                    logger.debug('User %s awarded %d XP (%d → %d, level %d)',
                                self.user.username, amount, old_xp, self.total_xp, self.current_level)

                return {
                    'xp_awarded': amount,
                    'total_xp': self.total_xp,
                    'leveled_up': leveled_up,
                    'new_level': new_level if leveled_up else None,
                    'old_level': old_level
                }

        except (DatabaseError, IntegrityError) as e:
            logger.error(
                'Database error awarding %d XP to user %s: %s',
                amount, self.user.username, str(e)
            )
            raise DatabaseError(f"Failed to award XP: {str(e)}") from e


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal to automatically create UserProfile when User is created.

    Args:
        sender: The model class (User)
        instance: The User instance being saved
        created: Boolean - True if this is a new User
        **kwargs: Additional keyword arguments
    """
    if created:
        try:
            UserProfile.objects.create(user=instance)
        except (IntegrityError, ValidationError, ValueError, DatabaseError) as e:
            # Log specific errors but don't crash user creation
            # IntegrityError: Profile already exists (duplicate)
            # ValidationError: Model validation failed
            # ValueError: Invalid field value
            # DatabaseError: Database connection/query issues
            logger.exception('Failed to create profile for user %s: %s', instance.username, str(e))


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal to save UserProfile when User is saved.

    Args:
        sender: The model class (User)
        instance: The User instance being saved
        **kwargs: Additional keyword arguments
    """
    if hasattr(instance, 'profile'):
        try:
            instance.profile.save()
        except (IntegrityError, ValidationError, ValueError, DatabaseError) as e:
            # Log specific errors but don't crash user save operation
            # IntegrityError: Database constraint violation
            # ValidationError: Model validation failed
            # ValueError: Invalid field value
            # DatabaseError: Database connection/query issues
            logger.exception('Failed to save profile for user %s: %s', instance.username, str(e))

class UserProgress(models.Model):
    """Track overall user learning progress and statistics"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='progress')
    total_minutes_studied = models.IntegerField(default=0)
    total_lessons_completed = models.IntegerField(default=0)
    total_quizzes_taken = models.IntegerField(default=0)
    overall_quiz_accuracy = models.FloatField(default=0.0)  # Percentage 0-100
    
    # Streak tracking
    current_streak = models.IntegerField(default=0, help_text="Number of consecutive days with activity")
    longest_streak = models.IntegerField(default=0, help_text="Longest streak ever achieved")
    last_activity_date = models.DateField(null=True, blank=True, help_text="Last date user completed a lesson")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "User Progress"

    def __str__(self):
        return f"Progress for {self.user.username}"
    
    def update_streak(self):
        """
        Update user's learning streak based on activity.
        Call this whenever user completes a lesson.
        """
        from datetime import date, timedelta
        
        today = date.today()
        
        if self.last_activity_date is None:
            # First activity ever
            self.current_streak = 1
            self.longest_streak = 1
            self.last_activity_date = today
        elif self.last_activity_date == today:
            # Already studied today, no change to streak
            pass
        elif self.last_activity_date == today - timedelta(days=1):
            # Studied yesterday, increment streak
            self.current_streak += 1
            self.longest_streak = max(self.longest_streak, self.current_streak)
            self.last_activity_date = today
        else:
            # Missed a day, reset streak
            self.current_streak = 1
            self.last_activity_date = today
        
        self.save(update_fields=['current_streak', 'longest_streak', 'last_activity_date'])

    def calculate_quiz_accuracy(self):
        """
        Calculate overall quiz accuracy from all quiz results.

        Performance optimized: Uses database aggregation instead of loading
        all quiz objects into memory.
        """
        # Use database aggregation for performance (single query)
        aggregates = self.user.quiz_results.aggregate(
            total_score=Sum('score'),
            total_questions=Sum('total_questions')
        )

        total_score = aggregates['total_score'] or 0
        total_possible = aggregates['total_questions'] or 0

        if total_possible == 0:
            return 0.0

        return round((total_score / total_possible) * 100, 1)

    def get_weekly_stats(self):
        """
        Get statistics for the current week.

        Performance optimized: Uses database aggregation to calculate stats
        in the database rather than loading all objects into Python memory.
        This reduces memory usage and improves speed, especially with large datasets.
        """
        one_week_ago = timezone.now() - timezone.timedelta(days=7)

        # Use database aggregation for lesson stats (single query)
        lesson_aggregates = self.user.lesson_completions.filter(
            completed_at__gte=one_week_ago
        ).aggregate(
            count=Count('id'),
            total_minutes=Sum('duration_minutes')
        )

        weekly_lessons = lesson_aggregates['count'] or 0
        weekly_minutes = lesson_aggregates['total_minutes'] or 0

        # Use database aggregation for quiz accuracy (single query)
        quiz_aggregates = self.user.quiz_results.filter(
            completed_at__gte=one_week_ago
        ).aggregate(
            total_score=Sum('score'),
            total_questions=Sum('total_questions')
        )

        total_score = quiz_aggregates['total_score'] or 0
        total_possible = quiz_aggregates['total_questions'] or 0
        weekly_accuracy = round((total_score / total_possible) * 100, 1) if total_possible > 0 else 0.0

        return {
            'weekly_minutes': weekly_minutes,
            'weekly_lessons': weekly_lessons,
            'weekly_accuracy': weekly_accuracy,
        }


class LessonCompletion(models.Model):
    """Record each time a user completes a lesson"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_completions')
    lesson_id = models.CharField(max_length=100)  # Reference to lesson (flexible for future)
    lesson_title = models.CharField(max_length=200, blank=True)
    duration_minutes = models.IntegerField(default=0)  # Time spent on this lesson
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']
        verbose_name_plural = "Lesson Completions"

    def __str__(self):
        return f"{self.user.username} completed {self.lesson_title or self.lesson_id}"


class QuizResult(models.Model):
    """Store quiz attempts and scores for accuracy calculation"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_results')
    quiz_id = models.CharField(max_length=100)  # Reference to quiz (flexible for future)
    quiz_title = models.CharField(max_length=200, blank=True)
    score = models.IntegerField(default=0)  # Number of correct answers
    total_questions = models.IntegerField(default=0)  # Total questions in quiz
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']
        verbose_name_plural = "Quiz Results"

    def __str__(self):
        return f"{self.user.username} - {self.quiz_title or self.quiz_id}: {self.score}/{self.total_questions}"

    @property
    def accuracy_percentage(self):
        """Calculate accuracy percentage for this quiz"""
        if self.total_questions == 0:
            return 0.0
        return round((self.score / self.total_questions) * 100, 1)


class OnboardingQuestion(models.Model):
    """Cached multiple choice questions for onboarding assessment"""
    question_number = models.IntegerField()
    question_text = models.TextField()
    language = models.CharField(max_length=50, default='Spanish')
    
    # Difficulty level (capped at B1)
    difficulty_level = models.CharField(
        max_length=2,
        choices=[
            ('A1', 'Beginner'),
            ('A2', 'Elementary'),
            ('B1', 'Intermediate')
        ]
    )
    
    # Multiple choice options
    option_a = models.CharField(max_length=500)
    option_b = models.CharField(max_length=500)
    option_c = models.CharField(max_length=500)
    option_d = models.CharField(max_length=500)
    
    # Answer and explanation
    correct_answer = models.CharField(max_length=1, help_text="Store 'A', 'B', 'C', or 'D'")
    explanation = models.TextField(blank=True)
    
    # Scoring (A1=1, A2=2, B1=3)
    difficulty_points = models.IntegerField(default=1)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Q{self.question_number} ({self.language} - {self.difficulty_level}): {self.question_text[:50]}..."
    
    class Meta:
        verbose_name = "Onboarding Question"
        verbose_name_plural = "Onboarding Questions"
        ordering = ['language', 'question_number']
        unique_together = ['language', 'question_number']


class OnboardingAttempt(models.Model):
    """Track onboarding assessment attempts (for both guests and authenticated users)"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='onboarding_attempts',
        null=True, 
        blank=True
    )
    session_key = models.CharField(max_length=100, blank=True, help_text="For guest tracking")
    language = models.CharField(max_length=50, default='Spanish')
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    calculated_level = models.CharField(
        max_length=2,
        choices=[
            ('A1', 'Beginner'),
            ('A2', 'Elementary'),
            ('B1', 'Intermediate')
        ],
        blank=True
    )
    total_score = models.IntegerField(default=0)
    total_possible = models.IntegerField(default=0)
    
    def __str__(self):
        user_display = self.user.username if self.user else f"Guest-{self.session_key[:8]}"
        return f"{user_display} - {self.language} ({self.calculated_level or 'In Progress'})"
    
    @property
    def score_percentage(self):
        """Calculate percentage score"""
        if self.total_possible == 0:
            return 0.0
        return round((self.total_score / self.total_possible) * 100, 1)
    
    class Meta:
        verbose_name = "Onboarding Attempt"
        verbose_name_plural = "Onboarding Attempts"
        ordering = ['-started_at']


class OnboardingAnswer(models.Model):
    """Individual answers within an onboarding attempt"""
    attempt = models.ForeignKey(
        OnboardingAttempt, 
        on_delete=models.CASCADE, 
        related_name='answers'
    )
    question = models.ForeignKey(
        OnboardingQuestion, 
        on_delete=models.CASCADE,
        related_name='user_answers'
    )
    
    # User's response
    user_answer = models.CharField(max_length=1, help_text="A, B, C, or D")
    is_correct = models.BooleanField()
    time_taken_seconds = models.IntegerField(default=0)
    
    answered_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} Q{self.question.question_number} - {self.user_answer}"

    class Meta:
        verbose_name = "Onboarding Answer"
        verbose_name_plural = "Onboarding Answers"
        ordering = ['question__question_number']


# =============================================================================
# LESSON MODELS
# =============================================================================

class Lesson(models.Model):
    """A language learning lesson"""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    language = models.CharField(max_length=50, default='Spanish')
    difficulty_level = models.CharField(
        max_length=2,
        choices=[
            ('A1', 'Beginner'),
            ('A2', 'Elementary'),
            ('B1', 'Intermediate')
        ],
        default='A1'
    )
    slug = models.SlugField(max_length=200, unique=True, blank=True, null=True, help_text="URL-friendly identifier for template paths (e.g., 'shapes', 'colors')")
    order = models.IntegerField(default=0, help_text="Order in lesson sequence")
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Daily Quest System fields (Sprint 3 - Issue #18)
    category = models.CharField(
        max_length=50,
        default='General',
        help_text='Category of lesson (e.g., Colors, Numbers, Shapes)'
    )
    lesson_type = models.CharField(
        max_length=20,
        choices=[('flashcard', 'Flashcard'), ('quiz', 'Quiz')],
        default='flashcard',
        help_text='Type of lesson content'
    )
    xp_value = models.IntegerField(
        default=100,
        help_text='XP awarded for completing this lesson'
    )

    # Link to next lesson
    next_lesson = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='previous_lesson'
    )

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Lesson"
        verbose_name_plural = "Lessons"

    def __str__(self):
        return f"{self.title} ({self.difficulty_level})"

    def save(self, *args, **kwargs):
        """
        Override save to auto-generate slug from title if not provided.
        Ensures unique slugs by appending a number if slug already exists.
        Handles race conditions by catching IntegrityError and retrying.
        """
        if not self.slug:
            # Generate base slug from title
            base_slug = slugify(self.title)
            self.slug = base_slug

        # Handle race conditions where multiple threads try to create same slug
        max_retries = 10
        for attempt in range(max_retries):
            try:
                super().save(*args, **kwargs)
                return  # Success, exit method
            except IntegrityError:
                # Slug collision occurred, generate a new unique slug
                if attempt == max_retries - 1:
                    # Max retries reached, re-raise the error
                    raise
                # Generate new slug with counter
                base_slug = slugify(self.title)
                self.slug = f"{base_slug}-{attempt + 1}"
                # Loop will retry save with new slug


class Flashcard(models.Model):
    """Flashcards for lessons"""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='cards')
    front_text = models.CharField(max_length=200)
    back_text = models.CharField(max_length=200)
    image_url = models.URLField(blank=True)
    audio_url = models.URLField(blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Flashcard"
        verbose_name_plural = "Flashcards"

    def __str__(self):
        return f"{self.front_text} → {self.back_text}"


class LessonQuizQuestion(models.Model):
    """Quiz questions for lessons"""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='quiz_questions')
    question = models.CharField(max_length=500)
    options = models.JSONField(help_text="List of answer options")
    correct_index = models.IntegerField(help_text="Index of correct answer (0-based)")
    explanation = models.TextField(blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = "Lesson Quiz Question"
        verbose_name_plural = "Lesson Quiz Questions"

    def __str__(self):
        return f"Q{self.order}: {self.question[:50]}..."


class LessonAttempt(models.Model):
    """Track user attempts at lesson quizzes"""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='attempts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='lesson_attempts')
    score = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']
        verbose_name = "Lesson Attempt"
        verbose_name_plural = "Lesson Attempts"

    def __str__(self):
        user_display = self.user.username if self.user else "Guest"
        return f"{user_display} - {self.lesson.title}: {self.score}/{self.total}"

    @property
    def percentage(self):
        """Calculate the percentage score for this lesson attempt."""
        if self.total == 0:
            return 0
        return round((self.score / self.total) * 100, 1)


# =============================================================================
# DAILY QUEST MODELS (Sprint 3 - Issue #18)
# =============================================================================

class DailyQuest(models.Model):
    """
    A daily quest generated from an existing lesson.
    Two quests per day: one time-based, one lesson-based.
    """
    # Identification
    date = models.DateField(db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField()

    # Source and Configuration
    based_on_lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    quest_type = models.CharField(max_length=20)  # 'study' (time-based), 'quiz' (lesson-based)

    # Rewards
    xp_reward = models.IntegerField()

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['date', 'quest_type']),
        ]
        # Allow two quests per day, but only one of each type
        unique_together = [['date', 'quest_type']]
        verbose_name = "Daily Quest"
        verbose_name_plural = "Daily Quests"

    def __str__(self):
        return f"Daily Quest - {self.date} - {self.quest_type} - {self.title}"


class DailyQuestQuestion(models.Model):
    """
    LEGACY MODEL - No longer used in current implementation.
    
    Daily quests now pull questions directly from lessons rather than
    storing pre-generated questions. This model is kept for:
    - Database migration compatibility
    - Historical test data
    
    Do not use this model for new features.
    
    Original purpose: A single question in a daily quest.
    Format depends on quest_type (flashcard vs quiz).
    """
    # Relationship
    daily_quest = models.ForeignKey(
        DailyQuest,
        on_delete=models.CASCADE,
        related_name='questions'
    )

    # Question Content
    question_text = models.TextField()

    # For flashcard type
    answer_text = models.CharField(max_length=200, blank=True)

    # For quiz type
    options = models.JSONField(default=list, blank=True)
    correct_index = models.IntegerField(null=True, blank=True)

    # Ordering
    order = models.IntegerField()  # 1-5

    # Metadata
    difficulty_level = models.CharField(max_length=10, default='medium')

    class Meta:
        ordering = ['order']
        unique_together = [['daily_quest', 'order']]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(order__gte=1) & models.Q(order__lte=5),
                name='valid_question_order'
            )
        ]
        verbose_name = "Daily Quest Question"
        verbose_name_plural = "Daily Quest Questions"

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}"


class UserDailyQuestAttempt(models.Model):
    """
    Tracks a user's attempt at a daily quest.
    One attempt per user per quest (one per day).
    """
    # Relationships
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    daily_quest = models.ForeignKey(
        DailyQuest,
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
        verbose_name = "User Daily Quest Attempt"
        verbose_name_plural = "User Daily Quest Attempts"

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
