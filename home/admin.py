from django.contrib import admin
from .models import UserProgress, LessonCompletion, QuizResult


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_minutes_studied', 'total_lessons_completed', 'total_quizzes_taken', 'overall_quiz_accuracy', 'updated_at')
    search_fields = ('user__username', 'user__email')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(LessonCompletion)
class LessonCompletionAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson_title', 'lesson_id', 'duration_minutes', 'completed_at')
    search_fields = ('user__username', 'lesson_title', 'lesson_id')
    list_filter = ('completed_at',)
    readonly_fields = ('completed_at',)


@admin.register(QuizResult)
class QuizResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz_title', 'quiz_id', 'score', 'total_questions', 'accuracy_percentage', 'completed_at')
    search_fields = ('user__username', 'quiz_title', 'quiz_id')
    list_filter = ('completed_at',)
    readonly_fields = ('completed_at',)
