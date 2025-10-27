"""
Admin interface tests.
Tests custom admin actions, CRUD operations, search/filters, and access control.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage

from home.models import UserProgress, LessonCompletion, QuizResult
from home.admin import CustomUserAdmin, UserProgressAdmin
from .test_utils import create_test_superuser, create_test_user, AdminTestCase


# =============================================================================
# ADMIN CUSTOM ACTIONS
# =============================================================================

class AdminCustomActionsTest(TestCase):
    """Test custom admin actions"""
    
    def setUp(self):
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldPass123!'
        )
    
    def test_reset_password_action(self):
        """Test password reset admin action"""
        from home.admin import reset_password_to_default
        
        request = HttpRequest()
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = User.objects.filter(username='testuser')
        
        old_password = self.test_user.password
        reset_password_to_default(CustomUserAdmin(User, AdminSite()), request, queryset)
        
        self.test_user.refresh_from_db()
        self.assertNotEqual(self.test_user.password, old_password)
    
    def test_make_staff_admin_action(self):
        """Test make staff admin action"""
        from home.admin import make_staff_admin
        
        request = HttpRequest()
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = User.objects.filter(username='testuser')
        
        make_staff_admin(CustomUserAdmin(User, AdminSite()), request, queryset)
        
        self.test_user.refresh_from_db()
        self.assertTrue(self.test_user.is_staff)
        self.assertTrue(self.test_user.is_superuser)
    
    def test_reset_user_progress_action(self):
        """Test reset progress admin action"""
        from home.admin import reset_user_progress
        
        progress = UserProgress.objects.create(
            user=self.test_user,
            total_minutes_studied=100,
            total_lessons_completed=10
        )
        LessonCompletion.objects.create(user=self.test_user, lesson_id='l1', duration_minutes=30)
        
        request = HttpRequest()
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        queryset = User.objects.filter(username='testuser')
        
        reset_user_progress(CustomUserAdmin(User, AdminSite()), request, queryset)
        
        progress.refresh_from_db()
        self.assertEqual(progress.total_minutes_studied, 0)
        self.assertEqual(self.test_user.lesson_completions.count(), 0)


# =============================================================================
# ADMIN ACCESS CONTROL
# =============================================================================

class AdminAccessControlTest(TestCase):
    """Test admin authentication and access"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = create_test_superuser()
        self.regular_user = create_test_user()
    
    def test_admin_login_successful(self):
        """Test admin can login"""
        response = self.client.post('/admin/login/', {
            'username': self.admin_user.username,
            'password': self.admin_user._test_password,
            'next': '/admin/'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/admin/'))
    
    def test_regular_user_cannot_access_admin(self):
        """Test regular user cannot access admin"""
        self.client.login(
            username=self.regular_user.username,
            password=self.regular_user._test_password
        )
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)
    
    def test_admin_can_access_user_changelist(self):
        """Test admin can view user list"""
        self.client.login(
            username=self.admin_user.username,
            password=self.admin_user._test_password
        )
        response = self.client.get('/admin/auth/user/')
        self.assertEqual(response.status_code, 200)


# =============================================================================
# ADMIN CRUD OPERATIONS
# =============================================================================

class AdminCRUDTest(AdminTestCase):
    """Test admin CRUD operations"""
    
    def test_create_user_progress(self):
        """Test creating UserProgress through admin"""
        test_user = create_test_user()
        response = self.client.post('/admin/home/userprogress/add/', {
            'user': test_user.pk,
            'total_minutes_studied': 100,
            'total_lessons_completed': 5,
            'total_quizzes_taken': 3,
            'overall_quiz_accuracy': 85.5,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UserProgress.objects.filter(user=test_user).exists())
    
    def test_edit_user_progress(self):
        """Test editing UserProgress through admin"""
        test_user = create_test_user()
        progress = UserProgress.objects.create(user=test_user, total_minutes_studied=50)
        
        response = self.client.post(f'/admin/home/userprogress/{progress.pk}/change/', {
            'user': test_user.pk,
            'total_minutes_studied': 150,
            'total_lessons_completed': 10,
            'total_quizzes_taken': 5,
            'overall_quiz_accuracy': 90.0,
        })
        
        progress.refresh_from_db()
        self.assertEqual(progress.total_minutes_studied, 150)


# =============================================================================
# ADMIN SEARCH AND FILTERS
# =============================================================================

class AdminSearchFilterTest(AdminTestCase):
    """Test admin search and filter functionality"""
    
    def test_user_search_by_username(self):
        """Test searching users by username"""
        user1 = User.objects.create_user(username='john', email='john@example.com')
        user2 = User.objects.create_user(username='jane', email='jane@example.com')
        
        response = self.client.get('/admin/auth/user/', {'q': 'john'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'john')
        self.assertNotContains(response, 'jane')
    
    def test_user_filter_by_staff_status(self):
        """Test filtering users by staff status"""
        user1 = User.objects.create_user(username='staff', email='staff@example.com', is_staff=True)
        user2 = User.objects.create_user(username='regular', email='regular@example.com')
        
        response = self.client.get('/admin/auth/user/', {'is_staff__exact': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'staff')
