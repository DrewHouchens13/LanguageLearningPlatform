from django.test import TestCase, Client
from django.contrib.auth.models import User

from home.models import UserProgress, LessonCompletion, QuizResult
from .test_utils import create_test_user, create_test_superuser, AdminTestCase

from django.http import HttpRequest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.messages import get_messages

from home.admin import (
    reset_password_to_default, make_staff_admin, remove_admin_privileges,
    reset_user_progress, reset_progress_stats, delete_selected_lessons, delete_selected_quizzes,
    delete_user_avatars, delete_user_avatars_from_users
)


# ============================================================================
# ADMIN TESTS
# ============================================================================

class TestAdminCustomActions(TestCase):
    """Test custom admin actions for user management"""

    def setUp(self):
        """Create test users and admin user"""
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldSecurePass456!@#'
        )
        self.test_user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='OldSecurePass456!@#'
        )

    def test_reset_password_to_default_action(self):
        """Test admin action to reset user password to secure random password"""
        from home.admin import reset_password_to_default
        from django.contrib.admin.sites import AdminSite
        from django.http import HttpRequest
        from django.contrib.auth.admin import UserAdmin
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.messages import get_messages

        # Store old password
        old_password = self.test_user.password

        # Create mock request and queryset
        request = HttpRequest()
        # Setup messages framework
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = User.objects.filter(username='testuser')

        # Execute the action
        reset_password_to_default(UserAdmin(User, AdminSite()), request, queryset)

        # Verify password was changed
        self.test_user.refresh_from_db()
        self.assertNotEqual(self.test_user.password, old_password)

        # Verify a message was sent with the new password
        messages = list(get_messages(request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Passwords reset for 1 user(s)', str(messages[0]))
        self.assertIn('SECURITY', str(messages[0]))  # Check for security warning
        self.assertIn('testuser:', str(messages[0]))  # Verify username in message

    def test_make_staff_admin_action(self):
        """Test admin action to make user an administrator"""
        from home.admin import make_staff_admin
        from django.contrib.admin.sites import AdminSite
        from django.http import HttpRequest
        from django.contrib.auth.admin import UserAdmin
        from django.contrib.messages.storage.fallback import FallbackStorage

        # Verify user is not admin initially
        self.assertFalse(self.test_user.is_staff)
        self.assertFalse(self.test_user.is_superuser)

        request = HttpRequest()
        # Setup messages framework
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = User.objects.filter(username='testuser')

        # Execute the action
        make_staff_admin(UserAdmin(User, AdminSite()), request, queryset)

        # Verify user is now admin
        self.test_user.refresh_from_db()
        self.assertTrue(self.test_user.is_staff)
        self.assertTrue(self.test_user.is_superuser)

    def test_remove_admin_privileges_action(self):
        """Test admin action to remove admin privileges"""
        from home.admin import remove_admin_privileges
        from django.contrib.admin.sites import AdminSite
        from django.http import HttpRequest
        from django.contrib.auth.admin import UserAdmin
        from django.contrib.messages.storage.fallback import FallbackStorage

        # Make user admin first
        self.test_user.is_staff = True
        self.test_user.is_superuser = True
        self.test_user.save()

        request = HttpRequest()
        # Setup messages framework
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = User.objects.filter(username='testuser')

        # Execute the action
        remove_admin_privileges(UserAdmin(User, AdminSite()), request, queryset)

        # Verify admin privileges removed
        self.test_user.refresh_from_db()
        self.assertFalse(self.test_user.is_staff)
        self.assertFalse(self.test_user.is_superuser)

    def test_reset_user_progress_action(self):
        """Test admin action to reset user progress"""
        from home.admin import reset_user_progress
        from django.contrib.admin.sites import AdminSite
        from django.http import HttpRequest
        from django.contrib.auth.admin import UserAdmin
        from django.contrib.messages.storage.fallback import FallbackStorage

        # Create progress data for user
        progress = UserProgress.objects.create(
            user=self.test_user,
            total_minutes_studied=100,
            total_lessons_completed=10,
            total_quizzes_taken=5,
            overall_quiz_accuracy=85.0
        )
        LessonCompletion.objects.create(
            user=self.test_user,
            lesson_id='lesson1',
            duration_minutes=30
        )
        QuizResult.objects.create(
            user=self.test_user,
            quiz_id='quiz1',
            score=8,
            total_questions=10
        )

        request = HttpRequest()
        # Setup messages framework
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = User.objects.filter(username='testuser')

        # Execute the action
        reset_user_progress(UserAdmin(User, AdminSite()), request, queryset)

        # Verify progress was reset
        progress.refresh_from_db()
        self.assertEqual(progress.total_minutes_studied, 0)
        self.assertEqual(progress.total_lessons_completed, 0)
        self.assertEqual(progress.total_quizzes_taken, 0)
        self.assertEqual(progress.overall_quiz_accuracy, 0.0)

        # Verify lesson completions and quiz results deleted
        self.assertEqual(self.test_user.lesson_completions.count(), 0)
        self.assertEqual(self.test_user.quiz_results.count(), 0)

    def test_reset_progress_stats_action(self):
        """Test admin action to reset UserProgress statistics"""
        from home.admin import reset_progress_stats
        from django.contrib.admin.sites import AdminSite
        from django.http import HttpRequest
        from home.admin import UserProgressAdmin
        from django.contrib.messages.storage.fallback import FallbackStorage

        # Create progress data
        progress = UserProgress.objects.create(
            user=self.test_user,
            total_minutes_studied=100,
            total_lessons_completed=10,
            total_quizzes_taken=5,
            overall_quiz_accuracy=85.0
        )

        request = HttpRequest()
        # Setup messages framework
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = UserProgress.objects.filter(user=self.test_user)

        # Execute the action
        reset_progress_stats(UserProgressAdmin(UserProgress, AdminSite()), request, queryset)

        # Verify stats were reset
        progress.refresh_from_db()
        self.assertEqual(progress.total_minutes_studied, 0)
        self.assertEqual(progress.total_lessons_completed, 0)
        self.assertEqual(progress.total_quizzes_taken, 0)
        self.assertEqual(progress.overall_quiz_accuracy, 0.0)

    def test_admin_page_accessible_for_superuser(self):
        """Test that admin page is accessible for superuser"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)

    def test_admin_page_not_accessible_for_regular_user(self):
        """Test that admin page is not accessible for regular user"""
        self.client.login(username='testuser', password='OldSecurePass456!@#')
        response = self.client.get('/admin/')
        # Should redirect to login page
        self.assertEqual(response.status_code, 302)

    def test_admin_user_list_display(self):
        """Test custom user admin list display"""
        from home.admin import CustomUserAdmin
        from django.contrib.admin.sites import AdminSite

        admin = CustomUserAdmin(User, AdminSite())

        expected_fields = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'date_joined', 'last_login')
        self.assertEqual(admin.list_display, expected_fields)

    def test_get_progress_info_with_progress(self):
        """Test get_progress_info displays user progress data"""
        from home.admin import CustomUserAdmin
        from django.contrib.admin.sites import AdminSite

        # Create user with progress
        _ = UserProgress.objects.create(
            user=self.test_user,
            total_minutes_studied=150,
            total_lessons_completed=10,
            total_quizzes_taken=5,
            overall_quiz_accuracy=85.0
        )

        # Create some lesson completions and quiz results
        LessonCompletion.objects.create(
            user=self.test_user,
            lesson_id='lesson1',
            duration_minutes=30
        )
        QuizResult.objects.create(
            user=self.test_user,
            quiz_id='quiz1',
            score=8,
            total_questions=10
        )

        admin = CustomUserAdmin(User, AdminSite())
        progress_info = admin.get_progress_info(self.test_user)

        # Verify progress data is displayed
        self.assertIn('Total Minutes: 150', progress_info)
        self.assertIn('Total Lessons: 10', progress_info)
        self.assertIn('Total Quizzes: 5', progress_info)
        self.assertIn('Quiz Accuracy: 85.0%', progress_info)
        self.assertIn('Lesson Completions: 1', progress_info)
        self.assertIn('Quiz Results: 1', progress_info)

    def test_get_progress_info_without_progress(self):
        """Test get_progress_info when user has no progress"""
        from home.admin import CustomUserAdmin
        from django.contrib.admin.sites import AdminSite

        admin = CustomUserAdmin(User, AdminSite())
        progress_info = admin.get_progress_info(self.test_user)

        # Verify "no progress" message
        self.assertEqual(progress_info, "No progress data yet")

    def test_delete_selected_lessons_action(self):
        """
        Test delete_selected_lessons admin action.

        Verifies that the bulk delete action removes lesson completions
        and displays a success message to the admin user.
        """
        from home.admin import delete_selected_lessons, LessonCompletionAdmin
        from django.contrib.admin.sites import AdminSite
        from django.http import HttpRequest
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.messages import get_messages

        # Create lesson completions
        _ = LessonCompletion.objects.create(
            user=self.test_user,
            lesson_id='lesson1',
            duration_minutes=30
        )
        _ = LessonCompletion.objects.create(
            user=self.test_user,
            lesson_id='lesson2',
            duration_minutes=45
        )

        # Verify they exist
        self.assertEqual(LessonCompletion.objects.count(), 2)

        request = HttpRequest()
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = LessonCompletion.objects.all()

        # Execute the action
        delete_selected_lessons(LessonCompletionAdmin(LessonCompletion, AdminSite()), request, queryset)

        # Verify lessons were deleted
        self.assertEqual(LessonCompletion.objects.count(), 0)

        # Verify exact success message was displayed
        # Note: Using assertEqual (not assertIn) to ensure exact message matching.
        # This is intentional - if the message changes, we WANT the test to fail
        # so we know to update it and maintain consistency with user expectations.
        messages = list(get_messages(request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Successfully deleted 2 lesson completion(s)')

    def test_delete_selected_quizzes_action(self):
        """
        Test delete_selected_quizzes admin action.

        Verifies that the bulk delete action removes quiz results
        and displays a success message to the admin user.
        """
        from home.admin import delete_selected_quizzes, QuizResultAdmin
        from django.contrib.admin.sites import AdminSite
        from django.http import HttpRequest
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.messages import get_messages

        # Create quiz results
        _ = QuizResult.objects.create(
            user=self.test_user,
            quiz_id='quiz1',
            score=8,
            total_questions=10
        )
        _ = QuizResult.objects.create(
            user=self.test_user,
            quiz_id='quiz2',
            score=15,
            total_questions=20
        )

        # Verify they exist
        self.assertEqual(QuizResult.objects.count(), 2)

        request = HttpRequest()
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = QuizResult.objects.all()

        # Execute the action
        delete_selected_quizzes(QuizResultAdmin(QuizResult, AdminSite()), request, queryset)

        # Verify quizzes were deleted
        self.assertEqual(QuizResult.objects.count(), 0)

        # Verify exact success message was displayed
        # Note: Using exact matching to catch any unintended message changes
        messages = list(get_messages(request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Successfully deleted 2 quiz result(s)')

    def test_delete_user_avatars_action(self):
        """Test delete_user_avatars admin action for content moderation"""
        from django.core.files.base import ContentFile
        from home.models import UserProfile

        # Set avatar directly without image processing
        profile = self.test_user.profile
        profile.avatar.save('test_avatar.jpg', ContentFile(b'fake image'), save=False)
        UserProfile.objects.filter(pk=profile.pk).update(avatar=profile.avatar.name)
        profile.refresh_from_db()

        # Verify avatar field is set
        self.assertTrue(profile.avatar)

        # Create request and add message storage
        request = HttpRequest()
        request.user = self.admin_user
        setattr(request, 'session', 'session')
        messages_storage = FallbackStorage(request)
        setattr(request, '_messages', messages_storage)

        # Execute action
        queryset = UserProfile.objects.filter(user=self.test_user)
        delete_user_avatars(None, request, queryset)

        # Verify avatar was deleted
        profile.refresh_from_db()
        self.assertFalse(profile.avatar)

        # Check success message
        messages = list(get_messages(request))
        self.assertEqual(len(messages), 1)
        self.assertIn('Successfully deleted 1 avatar', str(messages[0]))

    def test_delete_user_avatars_from_users_action(self):
        """Test delete_user_avatars_from_users admin action (User admin wrapper)"""
        from django.core.files.base import ContentFile
        from home.models import UserProfile

        # Set avatar directly without image processing
        profile = self.test_user.profile
        profile.avatar.save('test_avatar2.jpg', ContentFile(b'fake image 2'), save=False)
        UserProfile.objects.filter(pk=profile.pk).update(avatar=profile.avatar.name)
        profile.refresh_from_db()

        # User 2 has no avatar (uses Gravatar)

        # Verify avatar exists for user 1
        self.assertTrue(profile.avatar)

        # Create request and add message storage
        request = HttpRequest()
        request.user = self.admin_user
        setattr(request, 'session', 'session')
        messages_storage = FallbackStorage(request)
        setattr(request, '_messages', messages_storage)

        # Execute action on both users
        queryset = User.objects.filter(username__in=['testuser', 'testuser2'])
        delete_user_avatars_from_users(None, request, queryset)

        # Verify avatar was deleted for user 1
        profile.refresh_from_db()
        self.assertFalse(profile.avatar)

        # Check messages
        messages = list(get_messages(request))
        self.assertEqual(len(messages), 2)
        self.assertIn('Successfully deleted 1 avatar', str(messages[0]))
        self.assertIn('1 user(s) had no custom avatar', str(messages[1]))

    def test_delete_avatars_no_custom_avatars(self):
        """Test delete avatars action when no custom avatars exist"""
        from home.models import UserProfile

        # Both users use Gravatar (no custom avatars)

        # Create request and add message storage
        request = HttpRequest()
        request.user = self.admin_user
        setattr(request, 'session', 'session')
        messages_storage = FallbackStorage(request)
        setattr(request, '_messages', messages_storage)

        # Execute action
        queryset = UserProfile.objects.filter(user__in=[self.test_user, self.test_user2])
        delete_user_avatars(None, request, queryset)

        # Check info message
        messages = list(get_messages(request))
        self.assertEqual(len(messages), 1)
        self.assertIn('No custom avatars found', str(messages[0]))


# ============================================================================
# ADMIN CRUD TESTS
# ============================================================================

class TestAdminCRUDOperations(AdminTestCase):
    """Test admin CRUD operations for all models."""
    def test_delete_user_through_admin(self):
        """Test deleting a user through admin interface"""
        # Create a test user
        test_user = User.objects.create_user(
            username='deleteuser',
            email='delete@example.com',
            password='testpass123'
        )

        user_pk = test_user.pk

        # Delete the user
        response = self.client.post(f'/admin/auth/user/{user_pk}/delete/', {
            'post': 'yes',
        })

        # Should redirect after deletion
        self.assertEqual(response.status_code, 302)

        # User should be deleted
        self.assertFalse(User.objects.filter(pk=user_pk).exists())

    def test_create_user_progress_through_admin(self):
        """Test creating UserProgress through admin interface"""
        test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        response = self.client.post('/admin/home/userprogress/add/', {
            'user': test_user.pk,
            'total_minutes_studied': 100,
            'total_lessons_completed': 5,
            'total_quizzes_taken': 3,
            'overall_quiz_accuracy': 85.5,
        })

        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # Progress should be created
        self.assertTrue(UserProgress.objects.filter(user=test_user).exists())

    def test_edit_user_progress_through_admin(self):
        """Test editing UserProgress through admin interface"""
        test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        progress = UserProgress.objects.create(
            user=test_user,
            total_minutes_studied=50
        )

        _ = self.client.post(f'/admin/home/userprogress/{progress.pk}/change/', {
            'user': test_user.pk,
            'total_minutes_studied': 150,
            'total_lessons_completed': 10,
            'total_quizzes_taken': 5,
            'overall_quiz_accuracy': 90.0,
        })

        # Refresh from database
        progress.refresh_from_db()

        # Values should be updated
        self.assertEqual(progress.total_minutes_studied, 150)
        self.assertEqual(progress.total_lessons_completed, 10)

    def test_create_lesson_completion_through_admin(self):
        """Test creating LessonCompletion through admin interface"""
        test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        response = self.client.post('/admin/home/lessoncompletion/add/', {
            'user': test_user.pk,
            'lesson_id': 'lesson_001',
            'lesson_title': 'Introduction to Spanish',
            'duration_minutes': 30,
        })

        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # Lesson completion should be created
        self.assertTrue(LessonCompletion.objects.filter(lesson_id='lesson_001').exists())

    def test_create_quiz_result_through_admin(self):
        """Test creating QuizResult through admin interface"""
        test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        response = self.client.post('/admin/home/quizresult/add/', {
            'user': test_user.pk,
            'quiz_id': 'quiz_001',
            'quiz_title': 'Spanish Vocabulary',
            'score': 18,
            'total_questions': 20,
        })

        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)

        # Quiz result should be created
        self.assertTrue(QuizResult.objects.filter(quiz_id='quiz_001').exists())



# ============================================================================
# ADMIN SEARCH AND FILTER TESTS
# ============================================================================

class TestAdminSearchAndFilters(AdminTestCase):
    """Test admin search and filter functionality."""

    @classmethod
    def setUpTestData(cls):
        """Create reusable test data (runs once per test class)"""
        super().setUpTestData()  # Create admin user from base class

        # Create test users for search/filter testing
        cls.user1 = User.objects.create_user(
            username='john',
            email='john@example.com',
            first_name='John',
            last_name='Doe'
        )
        cls.user2 = User.objects.create_user(
            username='jane',
            email='jane@example.com',
            first_name='Jane',
            last_name='Smith'
        )

    def test_user_search_by_username(self):
        """Test searching users by username in admin"""
        response = self.client.get('/admin/auth/user/', {'q': 'john'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'john')
        self.assertNotContains(response, 'jane')

    def test_user_search_by_email(self):
        """Test searching users by email in admin"""
        response = self.client.get('/admin/auth/user/', {'q': 'jane@example.com'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'jane')

    def test_user_filter_by_staff_status(self):
        """Test filtering users by staff status"""
        # Make user1 staff
        self.user1.is_staff = True
        self.user1.save()

        response = self.client.get('/admin/auth/user/', {'is_staff__exact': '1'})

        self.assertEqual(response.status_code, 200)
        # Should show john (staff) and admin, but not jane
        self.assertContains(response, 'john')
        self.assertContains(response, 'admin')

    def test_user_progress_search(self):
        """Test searching user progress by username"""
        _ = UserProgress.objects.create(
            user=self.user1,
            total_minutes_studied=100
        )

        response = self.client.get('/admin/home/userprogress/', {'q': 'john'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'john')

    def test_lesson_completion_search(self):
        """Test searching lesson completions"""
        _ = LessonCompletion.objects.create(
            user=self.user1,
            lesson_id='spanish_101',
            lesson_title='Spanish Basics'
        )

        response = self.client.get('/admin/home/lessoncompletion/', {'q': 'Spanish'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Spanish Basics')

    def test_quiz_result_search(self):
        """Test searching quiz results"""
        _ = QuizResult.objects.create(
            user=self.user1,
            quiz_id='quiz_spanish_001',
            quiz_title='Spanish Vocabulary Quiz',
            score=18,
            total_questions=20
        )

        response = self.client.get('/admin/home/quizresult/', {'q': 'Vocabulary'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vocabulary')

    def test_admin_list_filters_present(self):
        """Test that admin list filters are configured"""
        from home.admin import CustomUserAdmin
        from django.contrib.admin.sites import AdminSite

        admin = CustomUserAdmin(User, AdminSite())

        # Verify list_filter is configured
        self.assertIsNotNone(admin.list_filter)
        self.assertIn('is_staff', admin.list_filter)
        self.assertIn('is_superuser', admin.list_filter)



# ============================================================================
# ADMIN LOGIN FLOW TESTS
# ============================================================================

class TestAdminLoginFlow(TestCase):
    """Test admin authentication and access control."""

    @classmethod
    def setUpTestData(cls):
        """Create reusable test data with factory methods (no hardcoded credentials)"""
        # Create admin user for authentication testing
        cls.admin_user = create_test_superuser()
        # Create regular user to test access denial
        cls.regular_user = create_test_user()

    def setUp(self):
        """Set up test client (runs before each test)"""
        self.client = Client()

    def test_admin_login_successful(self):
        """Test successful admin login"""
        response = self.client.post('/admin/login/', {
            'username': self.admin_user.username,
            'password': self.admin_user._test_password,
            'next': '/admin/'
        })

        # Should redirect to admin index
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/admin/'))

    def test_admin_login_invalid_credentials(self):
        """Test admin login with invalid credentials"""
        response = self.client.post('/admin/login/', {
            'username': self.admin_user.username,
            'password': 'wrongpassword',
        })

        # Should stay on login page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter the correct username and password')

    def test_regular_user_cannot_access_admin(self):
        """Test that regular users cannot access admin"""
        self.client.login(
            username=self.regular_user.username,
            password=self.regular_user._test_password
        )

        response = self.client.get('/admin/')

        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_admin_logout(self):
        """Test admin logout"""
        # Login first
        self.client.login(
            username=self.admin_user.username,
            password=self.admin_user._test_password
        )

        # Access admin to verify logged in
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)

        # Logout (requires POST in modern Django)
        response = self.client.post('/admin/logout/')

        # Should redirect or show logout confirmation
        self.assertIn(response.status_code, [200, 302])

        # Try to access admin again (should redirect to login)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)

    def test_admin_access_user_changelist(self):
        """Test admin can access user changelist"""
        self.client.login(
            username=self.admin_user.username,
            password=self.admin_user._test_password
        )

        response = self.client.get('/admin/auth/user/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select user to change')

    def test_admin_access_user_progress_changelist(self):
        """Test admin can access UserProgress changelist"""
        self.client.login(
            username=self.admin_user.username,
            password=self.admin_user._test_password
        )

        response = self.client.get('/admin/home/userprogress/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'user progress')

    def test_admin_access_lesson_completion_changelist(self):
        """Test admin can access LessonCompletion changelist"""
        self.client.login(
            username=self.admin_user.username,
            password=self.admin_user._test_password
        )

        response = self.client.get('/admin/home/lessoncompletion/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lesson completion')

    def test_admin_access_quiz_result_changelist(self):
        """Test admin can access QuizResult changelist"""
        self.client.login(
            username=self.admin_user.username,
            password=self.admin_user._test_password
        )

        response = self.client.get('/admin/home/quizresult/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'quiz result')

    def test_unauthenticated_user_redirected_to_login(self):
        """Test unauthenticated users are redirected to admin login"""
        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_admin_index_shows_models(self):
        """Test admin index page shows all registered models"""
        self.client.login(
            username=self.admin_user.username,
            password=self.admin_user._test_password
        )

        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 200)
        # Should show User Progress models (case-sensitive based on model verbose names)
        self.assertContains(response, 'User Progress')
        self.assertContains(response, 'Lesson Completions')
        self.assertContains(response, 'Quiz Results')

