"""
Setup test data for avatar deletion testing.

Creates:
- Admin user for testing
- Regular users with different avatar configurations
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO

def create_test_image(color, size=(200, 200)):
    """Create a simple test image"""
    img = Image.new('RGB', size, color=color)
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return ContentFile(buffer.read(), name='test_avatar.jpg')

print("Creating test users...")

# Create superuser
admin_user, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@example.com',
        'is_staff': True,
        'is_superuser': True,
        'first_name': 'Admin',
        'last_name': 'User'
    }
)
if created:
    admin_user.set_password('admin123')
    admin_user.save()
    print(f"[+] Created superuser: admin / admin123")
else:
    print(f"[+] Superuser already exists: admin")

# Create regular user with custom avatar
user1, created = User.objects.get_or_create(
    username='testuser1',
    defaults={
        'email': 'user1@example.com',
        'first_name': 'Test',
        'last_name': 'User One'
    }
)
if created:
    user1.set_password('test123')
    user1.save()
    # Add custom avatar (red image)
    user1.profile.avatar.save('user1_avatar.jpg', create_test_image('red'), save=True)
    print(f"[+] Created user with CUSTOM avatar: testuser1 / test123")
else:
    print(f"[+] User already exists: testuser1")

# Create regular user without custom avatar (uses Gravatar)
user2, created = User.objects.get_or_create(
    username='testuser2',
    defaults={
        'email': 'user2@example.com',
        'first_name': 'Test',
        'last_name': 'User Two'
    }
)
if created:
    user2.set_password('test123')
    user2.save()
    print(f"[+] Created user with GRAVATAR only: testuser2 / test123")
else:
    print(f"[+] User already exists: testuser2")

# Create user with custom avatar (blue image)
user3, created = User.objects.get_or_create(
    username='testuser3',
    defaults={
        'email': 'user3@example.com',
        'first_name': 'Test',
        'last_name': 'User Three'
    }
)
if created:
    user3.set_password('test123')
    user3.save()
    # Add custom avatar (blue image)
    user3.profile.avatar.save('user3_avatar.jpg', create_test_image('blue'), save=True)
    print(f"[+] Created user with CUSTOM avatar: testuser3 / test123")
else:
    print(f"[+] User already exists: testuser3")

print("\n" + "="*60)
print("TEST DATA SETUP COMPLETE!")
print("="*60)
print("\nLogin credentials:")
print("  Admin: admin / admin123")
print("  User1: testuser1 / test123 (custom RED avatar)")
print("  User2: testuser2 / test123 (Gravatar only)")
print("  User3: testuser3 / test123 (custom BLUE avatar)")
print("\nAccess admin at: http://localhost:8000/admin/")
print("="*60)
