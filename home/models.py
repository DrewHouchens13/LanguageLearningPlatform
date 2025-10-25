from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


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
