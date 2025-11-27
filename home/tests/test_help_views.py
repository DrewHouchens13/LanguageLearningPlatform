"""
Tests for Help/Wiki System Views

Following TDD: These tests are written BEFORE implementation.
Tests should initially fail (Red), then pass after implementation (Green).
"""

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class HelpPageAccessTests(TestCase):
    """Test help page accessibility for different user types"""

    def setUp(self):
        """Set up test client and users"""
        self.client = Client()

        # Create regular user
        self.regular_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True,
            is_superuser=True
        )

    def test_help_page_accessible_to_guest_users(self):
        """Guest users should be able to access help page without login"""
        response = self.client.get(reverse('help'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home/help.html')

    def test_help_page_accessible_to_logged_in_users(self):
        """Logged-in users should be able to access help page"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('help'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home/help.html')

    def test_help_page_accessible_to_admin_users(self):
        """Admin users should be able to access help page"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('help'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home/help.html')


class HelpPageContentTests(TestCase):
    """Test help page content for different user roles"""

    def setUp(self):
        """Set up test client and users"""
        self.client = Client()

        self.regular_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )

    def test_help_page_shows_user_guide_for_guests(self):
        """Guest users should see the User Guide"""
        response = self.client.get(reverse('help'))

        self.assertContains(response, 'Help & Documentation')
        self.assertContains(response, 'User Guide')

    def test_help_page_shows_user_guide_for_regular_users(self):
        """Regular users should see the User Guide"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('help'))

        self.assertContains(response, 'User Guide')
        self.assertContains(response, 'Getting Started')

    def test_help_page_hides_admin_guide_for_regular_users(self):
        """Regular users should NOT see the Admin Guide tab"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('help'))

        # Should see User Guide
        self.assertContains(response, 'User Guide')

        # Should NOT see Admin Guide tab
        self.assertNotContains(response, 'Admin Guide')

    def test_help_page_shows_both_guides_for_admin_users(self):
        """Admin users should see both User Guide and Admin Guide tabs"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('help'))

        # Should see both tabs
        self.assertContains(response, 'User Guide')
        self.assertContains(response, 'Admin Guide')

    def test_help_page_includes_user_guide_sections(self):
        """Help page should include main User Guide sections"""
        response = self.client.get(reverse('help'))

        # Check for key sections from USER_GUIDE.md
        self.assertContains(response, 'Getting Started')
        self.assertContains(response, 'Creating an Account')
        self.assertContains(response, 'Daily Quests')
        self.assertContains(response, 'Managing Your Account')

    def test_help_page_includes_admin_guide_sections_for_admins(self):
        """Admin help page should include Admin Guide sections"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('help'))

        # Check for key sections from ADMIN_GUIDE.md
        self.assertContains(response, 'Managing Users')
        self.assertContains(response, 'Managing Lessons')


class HelpPageStructureTests(TestCase):
    """Test help page structure and navigation elements"""

    def setUp(self):
        """Set up test client"""
        self.client = Client()

    def test_help_page_has_table_of_contents(self):
        """Help page should include a table of contents"""
        response = self.client.get(reverse('help'))

        self.assertContains(response, 'Table of Contents')

    def test_help_page_has_search_bar(self):
        """Help page should include a search bar"""
        response = self.client.get(reverse('help'))

        self.assertContains(response, 'search')
        self.assertContains(response, 'Search help articles')

    def test_help_page_has_breadcrumb_navigation(self):
        """Help page should include breadcrumb navigation"""
        response = self.client.get(reverse('help'))

        self.assertContains(response, 'Home')
        self.assertContains(response, 'Help')

    def test_help_page_has_back_to_top_button(self):
        """Help page should include a back-to-top button"""
        response = self.client.get(reverse('help'))

        self.assertContains(response, 'Back to Top')


class HelpPageContextTests(TestCase):
    """Test context data passed to help page template"""

    def setUp(self):
        """Set up test client and users"""
        self.client = Client()

        self.regular_user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        self.admin_user = User.objects.create_user(
            username='admin',
            password='adminpass123',
            is_staff=True
        )

    def test_help_context_includes_is_admin_false_for_guests(self):
        """Context should indicate guest is not admin"""
        response = self.client.get(reverse('help'))

        self.assertFalse(response.context['is_admin'])

    def test_help_context_includes_is_admin_false_for_regular_users(self):
        """Context should indicate regular user is not admin"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('help'))

        self.assertFalse(response.context['is_admin'])

    def test_help_context_includes_is_admin_true_for_admin_users(self):
        """Context should indicate admin user is admin"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('help'))

        self.assertTrue(response.context['is_admin'])

    def test_help_context_includes_user_guide_content(self):
        """Context should include user guide content"""
        response = self.client.get(reverse('help'))

        self.assertIn('user_guide', response.context)
        self.assertIsNotNone(response.context['user_guide'])

    def test_help_context_includes_admin_guide_for_admins(self):
        """Context should include admin guide for admin users"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('help'))

        self.assertIn('admin_guide', response.context)
        self.assertIsNotNone(response.context['admin_guide'])

    def test_help_context_excludes_admin_guide_for_regular_users(self):
        """Context should not include admin guide for regular users"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('help'))

        # admin_guide should be None or not in context
        admin_guide = response.context.get('admin_guide')
        self.assertIsNone(admin_guide)
