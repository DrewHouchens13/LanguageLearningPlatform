"""
Live test script for avatar upload functionality with Cloudinary.

This script tests the complete avatar upload flow:
1. Creates a test user
2. Uploads an avatar image
3. Verifies upload to Cloudinary
4. Checks avatar URL is accessible
5. Tests Gravatar fallback for users without avatars

Usage:
    python test_avatar_upload_live.py
"""
import os
import sys
import django
from io import BytesIO
from PIL import Image

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from home.models import UserProfile
from django.core.files.uploadedfile import SimpleUploadedFile

def create_test_image():
    """Create a test image in memory."""
    # Create a simple colored square image
    img = Image.new('RGB', (200, 200), color='blue')
    img_io = BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)
    return img_io

def test_cloudinary_configured():
    """Test that Cloudinary is properly configured."""
    print("=" * 70)
    print("TEST 1: Cloudinary Configuration")
    print("=" * 70)

    from django.conf import settings

    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
    api_key = os.environ.get('CLOUDINARY_API_KEY')
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')

    if not all([cloud_name, api_key, api_secret]):
        print("[FAIL] Cloudinary environment variables not set!")
        return False

    print(f"[OK] Cloud Name: {cloud_name}")
    print(f"[OK] API Key: {api_key[:4]}...{api_key[-4:]}")
    print(f"[OK] API Secret: {api_secret[:4]}...{api_secret[-4:]}")

    # Check if Cloudinary is in INSTALLED_APPS
    if 'cloudinary' not in settings.INSTALLED_APPS:
        print("[FAIL] Cloudinary not in INSTALLED_APPS!")
        return False

    print("[OK] Cloudinary apps loaded in Django")

    # Check storage backend
    storage_backend = settings.STORAGES.get('default', {}).get('BACKEND', '')
    if 'cloudinary' not in storage_backend.lower():
        print(f"[FAIL] Storage backend not using Cloudinary: {storage_backend}")
        return False

    print(f"[OK] Using Cloudinary storage backend")
    print()
    return True

def test_create_user():
    """Create a test user."""
    print("=" * 70)
    print("TEST 2: Create Test User")
    print("=" * 70)

    # Clean up any existing test user
    User.objects.filter(username='test_avatar_user').delete()

    user = User.objects.create_user(
        username='test_avatar_user',
        email='test_avatar@example.com',
        password='TestPass123!',
        first_name='Avatar',
        last_name='Tester'
    )

    print(f"[OK] Created user: {user.username}")
    print(f"[OK] Email: {user.email}")

    # Check if UserProfile was auto-created
    try:
        profile = UserProfile.objects.get(user=user)
        print(f"[OK] UserProfile auto-created: {profile}")
    except UserProfile.DoesNotExist:
        # Create it manually if signal didn't fire
        profile = UserProfile.objects.create(user=user)
        print(f"[OK] UserProfile created manually: {profile}")

    print()
    return user

def test_avatar_upload(user):
    """Test avatar upload via Django test client."""
    print("=" * 70)
    print("TEST 3: Avatar Upload")
    print("=" * 70)

    client = Client()

    # Login
    logged_in = client.login(username='test_avatar_user', password='TestPass123!')
    if not logged_in:
        print("[FAIL] Could not log in test user!")
        return False

    print("[OK] Logged in successfully")

    # Create test image
    img_io = create_test_image()
    uploaded_file = SimpleUploadedFile(
        "test_avatar.png",
        img_io.read(),
        content_type="image/png"
    )

    # Post avatar upload
    response = client.post('/account/', {
        'action': 'update_avatar',
        'avatar': uploaded_file
    })

    print(f"[OK] Upload response status: {response.status_code}")

    if response.status_code != 200:
        print(f"[FAIL] Unexpected response status: {response.status_code}")
        return False

    # Refresh user profile from database
    profile = UserProfile.objects.get(user=user)

    if not profile.avatar:
        print("[FAIL] Avatar field is empty after upload!")
        return False

    print(f"[OK] Avatar uploaded: {profile.avatar.name}")
    print(f"[OK] Avatar URL: {profile.avatar.url}")

    # Check if URL contains cloudinary
    if 'cloudinary' in profile.avatar.url.lower() or 'res.cloudinary.com' in profile.avatar.url.lower():
        print("[OK] Avatar URL is from Cloudinary CDN!")
    else:
        print(f"[WARNING] Avatar URL doesn't appear to be from Cloudinary: {profile.avatar.url}")

    print()
    return True

def test_avatar_accessible(user):
    """Test that uploaded avatar is accessible."""
    print("=" * 70)
    print("TEST 4: Avatar Accessibility")
    print("=" * 70)

    profile = UserProfile.objects.get(user=user)

    if not profile.avatar:
        print("[FAIL] No avatar to test!")
        return False

    avatar_url = profile.avatar.url
    print(f"[INFO] Avatar URL: {avatar_url}")

    # Try to access the URL
    import requests
    try:
        response = requests.get(avatar_url, timeout=10)
        if response.status_code == 200:
            print(f"[OK] Avatar is accessible (HTTP {response.status_code})")
            print(f"[OK] Content-Type: {response.headers.get('Content-Type', 'unknown')}")
            print(f"[OK] Content-Length: {len(response.content)} bytes")
            return True
        else:
            print(f"[FAIL] Avatar not accessible (HTTP {response.status_code})")
            return False
    except Exception as e:
        print(f"[FAIL] Could not access avatar: {str(e)}")
        return False

def test_gravatar_fallback():
    """Test Gravatar fallback for users without avatars."""
    print("=" * 70)
    print("TEST 5: Gravatar Fallback")
    print("=" * 70)

    # Create user without avatar
    User.objects.filter(username='test_gravatar_user').delete()

    user = User.objects.create_user(
        username='test_gravatar_user',
        email='test_gravatar@example.com',
        password='TestPass123!',
        first_name='Gravatar',
        last_name='User'
    )

    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)

    print(f"[OK] Created user without avatar: {user.username}")

    # Test get_avatar_url method (should fall back to Gravatar)
    avatar_url = profile.get_avatar_url()
    print(f"[OK] get_avatar_url(): {avatar_url}")

    if 'gravatar.com' in avatar_url:
        print("[OK] Falls back to Gravatar when no avatar uploaded")
        return True
    else:
        print(f"[FAIL] Expected Gravatar fallback, got: {avatar_url}")
        return False

def cleanup():
    """Clean up test data."""
    print("=" * 70)
    print("CLEANUP")
    print("=" * 70)

    # Delete test users
    deleted_count_1 = User.objects.filter(username='test_avatar_user').delete()[0]
    deleted_count_2 = User.objects.filter(username='test_gravatar_user').delete()[0]

    print(f"[OK] Deleted test_avatar_user: {deleted_count_1} objects")
    print(f"[OK] Deleted test_gravatar_user: {deleted_count_2} objects")
    print()

def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("CLOUDINARY AVATAR UPLOAD - LIVE TEST SUITE")
    print("=" * 70)
    print()

    results = []

    # Test 1: Cloudinary configured
    results.append(("Cloudinary Configuration", test_cloudinary_configured()))

    if not results[-1][1]:
        print("\n[FATAL] Cloudinary not configured. Cannot continue.")
        return False

    # Test 2: Create user
    user = test_create_user()
    if not user:
        print("\n[FATAL] Could not create test user. Cannot continue.")
        return False
    results.append(("Create Test User", True))

    # Test 3: Upload avatar
    results.append(("Avatar Upload", test_avatar_upload(user)))

    # Test 4: Avatar accessible
    if results[-1][1]:
        results.append(("Avatar Accessibility", test_avatar_accessible(user)))
    else:
        print("\n[SKIP] Skipping accessibility test (upload failed)")
        results.append(("Avatar Accessibility", False))

    # Test 5: Gravatar fallback
    results.append(("Gravatar Fallback", test_gravatar_fallback()))

    # Cleanup
    cleanup()

    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] All tests passed! Avatar upload with Cloudinary is working correctly!")
        return True
    else:
        print(f"\n[FAILED] {total - passed} test(s) failed. Check output above for details.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
