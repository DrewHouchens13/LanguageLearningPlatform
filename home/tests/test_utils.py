"""
Shared test utilities and helpers.
Used across all test modules for consistency.
"""
from django.contrib.auth.models import User
from django.test import Client, TestCase


def create_test_user(**kwargs):
    """
    Factory method to create test users with secure, randomly generated data.
    
    Args:
        **kwargs: Optional user attributes to override defaults
    
    Returns:
        User: Created user instance with _test_password attribute
    """
    from django.utils.crypto import get_random_string
    
    random_suffix = get_random_string(8, allowed_chars='0123456789')
    
    defaults = {
        'username': f'testuser_{random_suffix}',
        'email': f'test_{random_suffix}@example.com',
        'password': get_random_string(16),
    }
    defaults.update(kwargs)
    
    password = defaults.pop('password')
    user = User.objects.create_user(**defaults)
    user.set_password(password)
    user.save()
    
    user._test_password = password
    return user


def create_test_superuser(**kwargs):
    """
    Factory method to create test superusers.
    
    Returns:
        User: Created superuser instance with _test_password attribute
    """
    from django.utils.crypto import get_random_string
    
    random_suffix = get_random_string(8, allowed_chars='0123456789')
    
    defaults = {
        'username': f'admin_{random_suffix}',
        'email': f'admin_{random_suffix}@example.com',
        'password': get_random_string(16),
    }
    defaults.update(kwargs)
    
    password = defaults.pop('password')
    user = User.objects.create_superuser(**defaults)
    user.set_password(password)
    user.save()
    
    user._test_password = password
    return user


class AdminTestCase(TestCase):
    """Base class for admin-related tests with authenticated admin user."""
    
    @classmethod
    def setUpTestData(cls):
        """Create reusable admin user"""
        cls.admin_user = create_test_superuser()
    
    def setUp(self):
        """Set up test client and login as admin"""
        self.client = Client()
        self.client.login(
            username=self.admin_user.username,
            password=self.admin_user._test_password
        )

