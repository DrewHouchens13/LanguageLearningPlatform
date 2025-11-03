from django.db import models
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User
from django.utils import timezone
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
            except (IOError, OSError) as e:
                # Handle corrupted or invalid image files
                logger.error('Failed to process avatar image for user %s: %s', self.user.username, str(e))
                raise ValidationError('Invalid or corrupted image file. Please upload a valid PNG or JPG image.') from e
            except UnidentifiedImageError as e:
                # Handle unrecognized image formats
                logger.error('Unidentified image format for user %s: %s', self.user.username, str(e))
                raise ValidationError('Unrecognized image format. Please upload a valid PNG or JPG image.') from e
            except ValueError as e:
                # Handle invalid parameter values during image processing
                logger.error('Invalid image parameters for user %s: %s', self.user.username, str(e))
                raise ValidationError('Invalid image data. Please upload a different PNG or JPG image.') from e

        super().save(*args, **kwargs)


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
        except Exception as e:
            # Log error but don't crash user creation
            logger.error('Failed to create profile for user %s: %s', instance.username, str(e))


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
        except Exception as e:
            # Log error but don't crash user save operation
            logger.error('Failed to save profile for user %s: %s', instance.username, str(e))

class UserProgress(models.Model):
    """Track overall user learning progress and statistics"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='progress')
    total_minutes_studied = models.IntegerField(default=0)
    total_lessons_completed = models.IntegerField(default=0)
    total_quizzes_taken = models.IntegerField(default=0)
    overall_quiz_accuracy = models.FloatField(default=0.0)  # Percentage 0-100
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "User Progress"

    def __str__(self):
        return f"Progress for {self.user.username}"

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
    order = models.IntegerField(default=0, help_text="Order in lesson sequence")
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
        if self.total == 0:
            return 0
        return round((self.score / self.total) * 100, 1)
