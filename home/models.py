import hashlib
import logging
import os
from io import BytesIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import DatabaseError, IntegrityError, models, transaction
from django.db.models import Count, Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from PIL import Image, UnidentifiedImageError

from .language_registry import DEFAULT_LANGUAGE

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

    # Proficiency tracking (10-level system)
    proficiency_level = models.IntegerField(
        null=True,
        blank=True,
        help_text="Proficiency level 1-10 (1=absolute beginner, 10=advanced)"
    )

    # Onboarding state
    has_completed_onboarding = models.BooleanField(default=False)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)

    # Learning preferences
    target_language = models.CharField(max_length=50, default=DEFAULT_LANGUAGE)
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
    daily_challenge_language = models.CharField(
        max_length=50,
        blank=True,
        help_text="Locked daily challenge language for the current day"
    )
    daily_challenge_language_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the daily challenge language was last locked"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        level_display = f"Level {self.proficiency_level}" if self.proficiency_level else 'Not assessed'
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
        
        Also handles conversion of CEFR proficiency levels (A1, A2, B1) to integers (1, 2, 3).
        """
        # Convert CEFR level strings to integers if needed (defensive programming)
        if self.proficiency_level is not None and isinstance(self.proficiency_level, str):
            cefr_to_level = {'A1': 1, 'A2': 2, 'B1': 3}
            self.proficiency_level = cefr_to_level.get(self.proficiency_level.upper(), 1)
            logger.info('Converted CEFR proficiency level string to integer: %s', self.proficiency_level)
        
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


class UserLanguageProfile(models.Model):
    """
    Track per-language learning progress, onboarding status, and XP.

    Designed so users can study multiple languages in parallel without losing
    their overall profile statistics. Each record corresponds to one language
    for a given user.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='language_profiles'
    )
    language = models.CharField(max_length=50)

    # Onboarding / proficiency tracking (10-level system)
    proficiency_level = models.IntegerField(
        null=True,
        blank=True,
        help_text="Proficiency level 1-10 (1=absolute beginner, 10=advanced)"
    )
    has_completed_onboarding = models.BooleanField(default=False)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)

    # Study stats (per language)
    total_minutes_studied = models.IntegerField(default=0)
    total_lessons_completed = models.IntegerField(default=0)
    total_quizzes_taken = models.IntegerField(default=0)

    # XP + leveling mirrors global profile but scoped to the language
    total_xp = models.PositiveIntegerField(default=0)
    current_level = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Language Profile"
        verbose_name_plural = "User Language Profiles"
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'language'],
                name='unique_user_language_profile'
            )
        ]
        ordering = ['language']

    def __str__(self):
        return f"{self.user.username} - {self.language}"

    def get_proficiency_level_display(self):
        """
        Get human-readable proficiency level display.
        
        Returns:
            str: Formatted proficiency level (e.g., "Level 2", "Level 10")
        """
        if self.proficiency_level is None:
            return 'Not assessed'
        return f"Level {self.proficiency_level}"

    def save(self, *args, **kwargs):
        """Normalize language names for consistency."""
        if self.language:
            self.language = self.language.strip().title()
        super().save(*args, **kwargs)

    @staticmethod
    def _calculate_level_from_xp(total_xp):
        """Helper to calculate CEFR-like level progression from XP."""
        level = 1
        while total_xp >= UserProfile.get_xp_for_level(level + 1):
            level += 1
        return level

    def get_xp_to_next_level(self):
        """Return XP needed to reach the next level."""
        next_level = self.current_level + 1
        return max(0, UserProfile.get_xp_for_level(next_level) - self.total_xp)

    def get_progress_to_next_level(self):
        """Return percentage progress toward the next level."""
        current_level_xp = UserProfile.get_xp_for_level(self.current_level)
        next_level_xp = UserProfile.get_xp_for_level(self.current_level + 1)
        xp_span = next_level_xp - current_level_xp
        if xp_span <= 0:
            return 100.0
        xp_in_level = self.total_xp - current_level_xp
        return min(100.0, max(0.0, (xp_in_level / xp_span) * 100))

    @transaction.atomic
    def award_xp(self, amount):
        """
        Award XP scoped to this language profile.

        Mirrors UserProfile.award_xp but keeps progress per language.
        """
        if not isinstance(amount, (int, float)):
            raise TypeError(f"XP amount must be numeric, got {type(amount).__name__}")

        amount = int(amount)
        if amount < 0:
            raise ValueError(f"XP amount must be non-negative, got {amount}")
        if amount == 0:
            return {
                'xp_awarded': 0,
                'total_xp': self.total_xp,
                'leveled_up': False,
                'new_level': None,
                'old_level': self.current_level
            }

        max_positive_int = 2147483647
        if self.total_xp + amount > max_positive_int:
            raise ValueError(
                f"XP overflow: {self.total_xp} + {amount} = {self.total_xp + amount} "
                f"exceeds maximum ({max_positive_int})"
            )

        with transaction.atomic():
            old_level = self.current_level
            self.total_xp += amount
            new_level = self._calculate_level_from_xp(self.total_xp)
            leveled_up = new_level > old_level
            if leveled_up:
                self.current_level = new_level
                self.save(update_fields=['total_xp', 'current_level'])
            else:
                self.save(update_fields=['total_xp'])

            return {
                'xp_awarded': amount,
                'total_xp': self.total_xp,
                'leveled_up': leveled_up,
                'new_level': new_level if leveled_up else None,
                'old_level': old_level
            }

    def increment_minutes(self, minutes):
        """Utility to add study minutes safely."""
        if minutes <= 0:
            return
        self.total_minutes_studied += minutes
        self.save(update_fields=['total_minutes_studied'])

    def increment_lessons(self, count=1):
        """Increment total lessons completed by count (atomic update)."""
        if count <= 0:
            return
        self.total_lessons_completed += count
        self.save(update_fields=['total_lessons_completed'])

    def increment_quizzes(self, count=1):
        """Increment total quizzes taken by count (atomic update)."""
        if count <= 0:
            return
        self.total_quizzes_taken += count
        self.save(update_fields=['total_quizzes_taken'])


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
            UserLanguageProfile.objects.get_or_create(
                user=instance,
                language=DEFAULT_LANGUAGE
            )
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
    language = models.CharField(
        max_length=50,
        default=DEFAULT_LANGUAGE,
        help_text='Language associated with the completed lesson'
    )
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
    language = models.CharField(
        max_length=50,
        default=DEFAULT_LANGUAGE,
        help_text='Language associated with the quiz content'
    )
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
    language = models.CharField(max_length=50, default=DEFAULT_LANGUAGE)
    
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
    language = models.CharField(max_length=50, default=DEFAULT_LANGUAGE)
    
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
    """
    A language learning lesson.

    🤖 AI ASSISTANT: Core content unit for the curriculum system.
    - Each lesson belongs to one skill_category (vocabulary, grammar, etc.)
    - difficulty_level is 1-10 (not A1/A2/B1) matching the 10-level system
    - Lessons are grouped into LearningModules by language + difficulty_level

    RELATED FILES:
    - home/services/curriculum_generator.py - Creates lessons from templates
    - home/management/commands/seed_curriculum.py - Seeds lessons from fixtures
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    language = models.CharField(max_length=50, default=DEFAULT_LANGUAGE)

    # Curriculum system: 10-level proficiency
    difficulty_level = models.IntegerField(
        default=1,
        help_text="Proficiency level 1-10 (1=absolute beginner, 10=advanced)"
    )

    # Curriculum system: skill category (vocabulary, grammar, etc.)
    skill_category = models.ForeignKey(
        'SkillCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lessons',
        help_text="Skill this lesson teaches (vocabulary, grammar, etc.)"
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
        return f"{self.title} (Level {self.difficulty_level})"

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
    Quests are language-specific so every learner sees content
    aligned with their current study language.
    """
    # Identification
    date = models.DateField(db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    language = models.CharField(
        max_length=50,
        default=DEFAULT_LANGUAGE,
        db_index=True,
        help_text='Language this challenge targets (matches user profile language)'
    )

    # Source and Configuration
    based_on_lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    quest_type = models.CharField(max_length=20)  # 'quiz' (single-mode for now)

    # Rewards
    xp_reward = models.IntegerField()

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['date', 'language']),
            models.Index(fields=['language']),
        ]
        # One quest per language per day
        unique_together = [['date', 'language']]
        verbose_name = "Daily Quest"
        verbose_name_plural = "Daily Quests"

    def __str__(self):
        return f"Daily Quest - {self.date} - {self.language} - {self.title}"


class DailyQuestQuestion(models.Model):
    """
    A single question in a daily quest.

    Daily quests contain 5 random questions pulled from lessons.
    Questions are pre-generated and stored when the quest is created.
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


class DailyChallengeLog(models.Model):
    """
    Track how authenticated users satisfy the new daily challenge.

    Each user can have at most one record per calendar date noting whether
    they completed the challenge via lesson practice or new-language onboarding.
    """

    CHALLENGE_TYPES = [
        ('lesson', 'Lesson Completion'),
        ('onboarding', 'New Language Onboarding'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='daily_challenges'
    )
    date = models.DateField(default=timezone.now, db_index=True)
    completed_via = models.CharField(max_length=20, choices=CHALLENGE_TYPES)
    language = models.CharField(max_length=50, blank=True)
    xp_awarded = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        unique_together = [['user', 'date']]
        verbose_name = "Daily Challenge Log"
        verbose_name_plural = "Daily Challenge Logs"

    def __str__(self):
        return f"{self.user.username} - {self.date} ({self.completed_via})"


# =============================================================================
# ADAPTIVE CURRICULUM SYSTEM MODELS
# =============================================================================

class SkillCategory(models.Model):
    """
    Five core language learning skill categories.

    Each lesson focuses on ONE skill category. Skills are ordered 1-5 and
    determine the sequence of lessons within a learning module.

    🤖 AI ASSISTANT: This model supports the adaptive curriculum system.
    - Skills are seeded via data migration (vocabulary, grammar, conversation, reading, listening)
    - Each skill has an emoji icon for UI display
    - Order field determines lesson sequence within a level

    RELATED FILES:
    - home/services/adaptive_test_service.py - Uses skills for test composition
    - home/templates/curriculum/module_detail.html - Displays skill icons
    """

    SKILL_CHOICES = [
        ('vocabulary', 'Vocabulary'),
        ('grammar', 'Grammar'),
        ('conversation', 'Conversation'),
        ('reading', 'Reading'),
        ('listening', 'Listening'),
    ]

    name = models.CharField(
        max_length=50,
        choices=SKILL_CHOICES,
        unique=True,
        help_text="Skill category identifier"
    )
    description = models.TextField(
        help_text="Detailed description of what this skill covers"
    )
    icon = models.CharField(
        max_length=10,
        help_text="Emoji icon for UI display (e.g., 📚, 📝, 💬, 📖, 🎧)"
    )
    order = models.IntegerField(
        help_text="Order in lesson sequence within a level (1-5)"
    )

    class Meta:
        ordering = ['order']
        verbose_name = "Skill Category"
        verbose_name_plural = "Skill Categories"

    def __str__(self):
        return f"{self.icon} {self.get_name_display()}"


class LearningModule(models.Model):
    """
    Groups 5 lessons + 1 adaptive test for a proficiency level.

    Each language has 10 learning modules (levels 1-10). Users must complete
    all 5 lessons in a module before taking the adaptive test. Scoring 85%+
    on the test advances the user to the next level.

    🤖 AI ASSISTANT: Central organizing unit for curriculum.
    - One module per language per level (100 total: 10 languages × 10 levels)
    - passing_score determines advancement threshold (default 85%)
    - get_lessons() returns ordered lessons by skill category

    RELATED FILES:
    - home/services/adaptive_test_service.py - Generates tests for modules
    - home/management/commands/seed_curriculum.py - Creates modules from fixtures
    """

    language = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Target language for this module"
    )
    proficiency_level = models.IntegerField(
        db_index=True,
        help_text="Level 1-10 (1=absolute beginner, 10=advanced)"
    )
    name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Human-readable module name (e.g., 'Basics', 'Daily Life')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of topics covered in this level"
    )
    passing_score = models.IntegerField(
        default=85,
        help_text="Minimum percentage score to advance to next level"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['language', 'proficiency_level']
        ordering = ['language', 'proficiency_level']
        verbose_name = "Learning Module"
        verbose_name_plural = "Learning Modules"
        indexes = [
            models.Index(fields=['language', 'proficiency_level']),
        ]

    def __str__(self):
        return f"{self.language} Level {self.proficiency_level}: {self.name or 'Unnamed'}"

    def get_lessons(self):
        """
        Get 5 lessons for this module in skill order.

        Returns:
            QuerySet: Lessons ordered by skill_category__order
        """
        return Lesson.objects.filter(
            language=self.language,
            difficulty_level=self.proficiency_level,
            is_published=True
        ).select_related('skill_category').order_by('skill_category__order')


class UserModuleProgress(models.Model):
    """
    Track user's progress through a learning module.

    Records which lessons are completed, test attempts, and overall
    module completion status. Users can only take the test after
    completing all 5 lessons.

    🤖 AI ASSISTANT: Core progress tracking for curriculum.
    - lessons_completed is a JSON list of completed lesson IDs
    - best_test_score tracks highest test performance
    - last_test_date enables 24-hour retry cooldown for failed tests

    RELATED FILES:
    - home/views.py - curriculum views update this model
    - home/services/adaptive_test_service.py - Updates on test completion
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='module_progress'
    )
    module = models.ForeignKey(
        LearningModule,
        on_delete=models.CASCADE,
        related_name='user_progress'
    )

    # Lesson completion tracking
    lessons_completed = models.JSONField(
        default=list,
        help_text="List of completed lesson IDs"
    )

    # Test tracking
    test_attempts = models.IntegerField(
        default=0,
        help_text="Number of test attempts"
    )
    best_test_score = models.FloatField(
        default=0.0,
        help_text="Highest test score achieved (percentage)"
    )
    last_test_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last test attempt"
    )

    # State
    is_module_complete = models.BooleanField(
        default=False,
        help_text="True when user passes test with 85%+"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when module was completed"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'module']
        ordering = ['module__language', 'module__proficiency_level']
        verbose_name = "User Module Progress"
        verbose_name_plural = "User Module Progress"
        indexes = [
            models.Index(fields=['user', 'is_module_complete']),
        ]

    def __str__(self):
        status = "✓" if self.is_module_complete else f"{len(self.lessons_completed)}/5"
        return f"{self.user.username} - {self.module} [{status}]"

    def all_lessons_completed(self):
        """Check if all 5 lessons in the module are completed."""
        return len(self.lessons_completed) >= 5

    def can_take_test(self):
        """
        Check if user can take the module test.

        Returns:
            bool: True if all lessons completed
        """
        return self.all_lessons_completed()

    def can_retry_test(self):
        """
        Check if user can retry the test (10-minute cooldown after failure).

        Returns:
            bool: True if no previous attempt or 10+ minutes since last attempt
        """
        if self.last_test_date is None:
            return True
        time_since_last = timezone.now() - self.last_test_date
        return time_since_last.total_seconds() >= 600  # 10 minutes

    def mark_lesson_complete(self, lesson_id):
        """
        Mark a lesson as completed.

        Args:
            lesson_id: ID of the completed lesson
        """
        if lesson_id not in self.lessons_completed:
            self.lessons_completed.append(lesson_id)
            self.save(update_fields=['lessons_completed', 'updated_at'])


class UserSkillMastery(models.Model):
    """
    Track user's mastery percentage per skill category.

    Used by the adaptive test service to generate personalized tests.
    Mastery is calculated from a rolling window of the last 50 question
    attempts per skill.

    🤖 AI ASSISTANT: Drives adaptive test composition.
    - mastery_percentage determines if skill is "weak" (<60%) or "strong" (>=60%)
    - Tests are 70% weak skills, 30% strong skills
    - Updated after every quiz/test submission

    RELATED FILES:
    - home/services/adaptive_test_service.py - Queries mastery for test generation
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='skill_mastery'
    )
    skill_category = models.ForeignKey(
        SkillCategory,
        on_delete=models.CASCADE,
        related_name='user_mastery'
    )
    language = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Language this mastery applies to"
    )

    # Rolling statistics (based on last 50 questions)
    total_attempts = models.IntegerField(
        default=0,
        help_text="Total questions attempted for this skill"
    )
    correct_attempts = models.IntegerField(
        default=0,
        help_text="Total correct answers for this skill"
    )
    mastery_percentage = models.FloatField(
        default=0.0,
        help_text="Mastery level as percentage (0-100)"
    )
    last_practiced = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time user practiced this skill"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'skill_category', 'language']
        ordering = ['language', 'skill_category__order']
        verbose_name = "User Skill Mastery"
        verbose_name_plural = "User Skill Mastery"
        indexes = [
            models.Index(fields=['user', 'language']),
            models.Index(fields=['user', 'language', 'mastery_percentage']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.language} {self.skill_category.name}: {self.mastery_percentage:.1f}%"

    def is_weak_skill(self):
        """Return True if mastery is below 60% (weak skill)."""
        return self.mastery_percentage < 60.0

    def update_mastery(self, is_correct):
        """
        Update mastery after a question attempt.

        Uses a rolling window approach: recent performance weighted more heavily.

        Args:
            is_correct: Boolean indicating if the answer was correct
        """
        self.total_attempts += 1
        if is_correct:
            self.correct_attempts += 1

        # Calculate mastery percentage
        if self.total_attempts > 0:
            self.mastery_percentage = (self.correct_attempts / self.total_attempts) * 100

        self.last_practiced = timezone.now()
        self.save(update_fields=[
            'total_attempts', 'correct_attempts',
            'mastery_percentage', 'last_practiced', 'updated_at'
        ])


class UserQuestionAttempt(models.Model):
    """
    Track individual question responses for mastery calculation.

    Records every question a user answers across lessons and tests.
    Used for detailed analytics and skill mastery recalculation.

    🤖 AI ASSISTANT: Granular tracking for analytics.
    - Links to both the question and the skill category
    - time_taken_seconds can identify struggling areas
    - Used to recalculate UserSkillMastery when needed

    RELATED FILES:
    - home/views.py - Creates records on quiz submission
    - home/services/adaptive_test_service.py - Creates records on test submission
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='question_attempts'
    )
    question = models.ForeignKey(
        LessonQuizQuestion,
        on_delete=models.CASCADE,
        related_name='user_attempts'
    )
    skill_category = models.ForeignKey(
        SkillCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='question_attempts',
        help_text="Skill category of the question (for analytics)"
    )

    is_correct = models.BooleanField(
        help_text="Whether the user answered correctly"
    )
    user_answer = models.IntegerField(
        null=True,
        blank=True,
        help_text="Index of the answer the user selected"
    )
    time_taken_seconds = models.IntegerField(
        default=0,
        help_text="Time spent on this question"
    )
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-answered_at']
        verbose_name = "User Question Attempt"
        verbose_name_plural = "User Question Attempts"
        indexes = [
            models.Index(fields=['user', '-answered_at']),
            models.Index(fields=['user', 'skill_category']),
        ]

    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} {self.user.username} - Q{self.question.id}"
class Badge(models.Model):
    """Achievement badges that users can earn"""
    BADGE_TYPES = [
        ('first_lesson', 'First Lesson'),
        ('perfect_score', 'Perfect Score'),
        ('five_lessons', 'Dedicated Learner'),
        ('ten_lessons', 'Language Explorer'),
        ('streak_3', '3 Day Streak'),
        ('streak_7', '7 Day Streak'),
        ('quiz_master', 'Quiz Master'),
    ]
    
    name = models.CharField(max_length=100)
    badge_type = models.CharField(max_length=50, choices=BADGE_TYPES, unique=True)
    description = models.TextField()
    icon = models.CharField(max_length=10, default='🏆')  # Emoji icon
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class UserBadge(models.Model):
    """Tracks which badges users have earned"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'badge')
        ordering = ['-earned_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"
