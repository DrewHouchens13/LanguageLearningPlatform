from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO
import hashlib
import os


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
    Extended user profile with avatar support.

    Uses hybrid approach:
    - Gravatar as default (based on email)
    - Optional custom avatar upload
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(
        upload_to=user_avatar_path,
        blank=True,
        null=True,
        help_text="Profile picture (max 5MB, PNG/JPG only)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.username}"

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
            # Open the uploaded image
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
        UserProfile.objects.create(user=instance)


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
        instance.profile.save()


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
        """Calculate overall quiz accuracy from all quiz results"""
        quiz_results = self.user.quiz_results.all()
        if not quiz_results.exists():
            return 0.0
        
        total_score = sum(result.score for result in quiz_results)
        total_possible = sum(result.total_questions for result in quiz_results)
        
        if total_possible == 0:
            return 0.0
        
        return round((total_score / total_possible) * 100, 1)

    def get_weekly_stats(self):
        """
        Get statistics for the current week.

        Optimized to minimize database queries by reusing querysets.
        """
        one_week_ago = timezone.now() - timezone.timedelta(days=7)

        # Fetch weekly lessons once and reuse (avoids duplicate query)
        weekly_completions = self.user.lesson_completions.filter(
            completed_at__gte=one_week_ago
        )
        weekly_lessons = weekly_completions.count()
        weekly_minutes = sum(completion.duration_minutes for completion in weekly_completions)

        # Weekly quiz accuracy
        weekly_quizzes = self.user.quiz_results.filter(
            completed_at__gte=one_week_ago
        )
        if weekly_quizzes.exists():
            total_score = sum(result.score for result in weekly_quizzes)
            total_possible = sum(result.total_questions for result in weekly_quizzes)
            weekly_accuracy = round((total_score / total_possible) * 100, 1) if total_possible > 0 else 0.0
        else:
            weekly_accuracy = 0.0

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
