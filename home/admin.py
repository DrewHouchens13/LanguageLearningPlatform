from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UserProgress, LessonCompletion, QuizResult
import secrets
import string
import logging

# Configure logger for admin actions (audit trail)
logger = logging.getLogger(__name__)


# Custom actions for User admin
def reset_password_to_default(modeladmin, request, queryset):
    """
    Reset selected users' passwords to a cryptographically secure random password.

    SECURITY NOTE: Passwords are displayed ONE TIME in the admin interface.
    This is intentional design because:
    1. Email system is not yet configured for automated delivery
    2. Admin must securely communicate password to user via secure channel
    3. This is displayed ONLY to superusers in the admin interface
    4. Passwords are NOT logged or stored in plaintext

    Alternative (recommended for production with email configured):
    - Send password reset link via email instead of displaying password
    - Use Django's PasswordResetForm for secure token-based reset

    Uses Python's secrets module for cryptographically strong randomness,
    which is recommended for security-sensitive applications like password generation.

    Args:
        modeladmin: The ModelAdmin instance
        request: HttpRequest object
        queryset: QuerySet of User objects to reset
    """
    reset_info = []
    failed_users = []

    for user in queryset:
        try:
            # Generate a cryptographically secure random password (16 characters)
            # Using secrets.choice() for each character ensures cryptographic randomness
            alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
            new_password = ''.join(secrets.choice(alphabet) for _ in range(16))
            user.set_password(new_password)
            user.save()
            reset_info.append(f"{user.username}: {new_password}")

            # Log admin action for audit trail (password NOT logged, only action)
            admin_user = getattr(request, 'user', None)
            admin_username = admin_user.username if admin_user else 'Unknown'
            logger.info(
                'Admin %s reset password for user: %s', admin_username, user.username
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Handle save failures gracefully (catch all to avoid breaking batch operation)
            failed_users.append(user.username)
            logger.error(
                'Failed to reset password for user %s: %s', user.username, str(e)
            )

    # Display passwords to admin (one-time only, must communicate securely to users)
    # WARNING: Admin must copy these passwords immediately and transmit via secure channel
    if reset_info:
        passwords_msg = " | ".join(reset_info)
        messages.warning(
            request,
            f'⚠️ SECURITY: Passwords reset for {len(reset_info)} user(s). '
            f'Copy these NOW and communicate via secure channel. '
            f'They will not be shown again: {passwords_msg}'
        )

    # Report any failures
    if failed_users:
        messages.error(
            request,
            f'Failed to reset passwords for: {", ".join(failed_users)}'
        )
reset_password_to_default.short_description = "Reset passwords (generates secure random passwords)"


def make_staff_admin(modeladmin, request, queryset):
    """Make selected users staff and superuser (admin)"""
    count = queryset.update(is_staff=True, is_superuser=True)
    messages.success(request, f'Successfully made {count} user(s) administrators')
make_staff_admin.short_description = "Make selected users administrators"


def remove_admin_privileges(modeladmin, request, queryset):
    """Remove admin privileges from selected users"""
    count = queryset.update(is_staff=False, is_superuser=False)
    messages.success(request, f'Successfully removed admin privileges from {count} user(s)')
remove_admin_privileges.short_description = "Remove admin privileges"


def reset_user_progress(modeladmin, request, queryset):
    """Reset all progress data for selected users"""
    count = 0
    for user in queryset:
        # Delete all lesson completions
        user.lesson_completions.all().delete()
        # Delete all quiz results
        user.quiz_results.all().delete()
        # Reset user progress stats
        if hasattr(user, 'progress'):
            user.progress.total_minutes_studied = 0
            user.progress.total_lessons_completed = 0
            user.progress.total_quizzes_taken = 0
            user.progress.overall_quiz_accuracy = 0.0
            user.progress.save()
        count += 1
    messages.success(request, f'Successfully reset all progress for {count} user(s)')
reset_user_progress.short_description = "Reset all user progress"


# Unregister the default User admin and register custom one
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    """Enhanced User admin with custom actions"""
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'date_joined', 'last_login')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    actions = [reset_password_to_default, make_staff_admin, remove_admin_privileges, reset_user_progress]

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Progress Information', {
            'fields': ('get_progress_info',),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = BaseUserAdmin.readonly_fields + ('get_progress_info',)

    def get_progress_info(self, obj):
        """Display user progress information in admin"""
        if hasattr(obj, 'progress'):
            progress = obj.progress
            return f"""
            Total Minutes: {progress.total_minutes_studied}
            Total Lessons: {progress.total_lessons_completed}
            Total Quizzes: {progress.total_quizzes_taken}
            Quiz Accuracy: {progress.overall_quiz_accuracy}%
            Lesson Completions: {obj.lesson_completions.count()}
            Quiz Results: {obj.quiz_results.count()}
            """
        return "No progress data yet"
    get_progress_info.short_description = "User Progress Summary"


# Custom actions for UserProgress admin
def reset_progress_stats(modeladmin, request, queryset):
    """Reset progress statistics to zero"""
    count = queryset.update(
        total_minutes_studied=0,
        total_lessons_completed=0,
        total_quizzes_taken=0,
        overall_quiz_accuracy=0.0
    )
    messages.success(request, f'Successfully reset {count} user progress record(s)')
reset_progress_stats.short_description = "Reset progress statistics"


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_minutes_studied', 'total_lessons_completed', 'total_quizzes_taken', 'overall_quiz_accuracy', 'updated_at')
    search_fields = ('user__username', 'user__email')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    actions = [reset_progress_stats]

    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Progress Statistics', {
            'fields': ('total_minutes_studied', 'total_lessons_completed', 'total_quizzes_taken', 'overall_quiz_accuracy')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# Custom actions for LessonCompletion admin
def delete_selected_lessons(modeladmin, request, queryset):
    """Delete selected lesson completions"""
    count = queryset.count()
    queryset.delete()
    messages.success(request, f'Successfully deleted {count} lesson completion(s)')
delete_selected_lessons.short_description = "Delete selected lesson completions"


@admin.register(LessonCompletion)
class LessonCompletionAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson_title', 'lesson_id', 'duration_minutes', 'completed_at')
    search_fields = ('user__username', 'lesson_title', 'lesson_id')
    list_filter = ('completed_at',)
    readonly_fields = ('completed_at',)
    actions = [delete_selected_lessons]


# Custom actions for QuizResult admin
def delete_selected_quizzes(modeladmin, request, queryset):
    """Delete selected quiz results"""
    count = queryset.count()
    queryset.delete()
    messages.success(request, f'Successfully deleted {count} quiz result(s)')
delete_selected_quizzes.short_description = "Delete selected quiz results"


@admin.register(QuizResult)
class QuizResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz_title', 'quiz_id', 'score', 'total_questions', 'accuracy_percentage', 'completed_at')
    search_fields = ('user__username', 'quiz_title', 'quiz_id')
    list_filter = ('completed_at',)
    readonly_fields = ('completed_at',)
    actions = [delete_selected_quizzes]
