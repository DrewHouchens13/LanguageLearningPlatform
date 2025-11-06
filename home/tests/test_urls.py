from django.test import TestCase
from django.urls import reverse, resolve

from home.views import account_view, forgot_password_view, reset_password_view, forgot_username_view


# ============================================================================
# URL ROUTING TESTS FOR NEW VIEWS
# ============================================================================

class AccountManagementURLTests(TestCase):
    """Tests for account management URL routing"""

    def test_account_url_resolves(self):
        """Test /account/ URL resolves to account_view"""
        url = reverse('account')
        self.assertEqual(resolve(url).func, account_view)

    def test_forgot_password_url_resolves(self):
        """Test /forgot-password/ URL resolves to forgot_password_view"""
        url = reverse('forgot_password')
        self.assertEqual(resolve(url).func, forgot_password_view)

    def test_reset_password_url_resolves(self):
        """Test /reset-password/<uidb64>/<token>/ URL resolves"""
        url = reverse('reset_password', kwargs={'uidb64': 'MQ', 'token': 'abc123'})
        self.assertEqual(resolve(url).func, reset_password_view)

    def test_forgot_username_url_resolves(self):
        """Test /forgot-username/ URL resolves to forgot_username_view"""
        url = reverse('forgot_username')
        self.assertEqual(resolve(url).func, forgot_username_view)

