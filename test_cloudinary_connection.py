"""
Diagnostic script to test Cloudinary configuration on Render.

Run this on Render to diagnose avatar upload issues:
python test_cloudinary_connection.py
"""
import os
import sys

def test_cloudinary_env_vars():
    """Test if Cloudinary environment variables are set."""
    print("=" * 60)
    print("CLOUDINARY ENVIRONMENT VARIABLES TEST")
    print("=" * 60)

    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
    api_key = os.environ.get('CLOUDINARY_API_KEY')
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')

    print(f"CLOUDINARY_CLOUD_NAME: {'[OK] SET' if cloud_name else '[X] NOT SET'}")
    if cloud_name:
        print(f"  Value: {cloud_name}")

    print(f"CLOUDINARY_API_KEY: {'[OK] SET' if api_key else '[X] NOT SET'}")
    if api_key:
        print(f"  Value: {api_key}")

    print(f"CLOUDINARY_API_SECRET: {'[OK] SET' if api_secret else '[X] NOT SET'}")
    if api_secret:
        # Only show first/last 4 chars for security
        masked = api_secret[:4] + '*' * (len(api_secret) - 8) + api_secret[-4:]
        print(f"  Value: {masked}")

    return bool(cloud_name and api_key and api_secret)


def test_cloudinary_import():
    """Test if cloudinary packages can be imported."""
    print("\n" + "=" * 60)
    print("CLOUDINARY PACKAGE IMPORT TEST")
    print("=" * 60)

    try:
        import cloudinary
        print(f"[OK] cloudinary package imported successfully")
        try:
            print(f"  Version: {cloudinary.__version__}")
        except AttributeError:
            # cloudinary module doesn't have __version__ in older versions
            print(f"  Version: (version info not available)")
    except ImportError as e:
        print(f"[X] Failed to import cloudinary: {e}")
        return False

    try:
        import cloudinary_storage
        print(f"[OK] cloudinary_storage package imported successfully")
        # cloudinary_storage doesn't have __version__ attribute
        print(f"  Package: {cloudinary_storage.__name__}")
    except ImportError as e:
        print(f"[X] Failed to import cloudinary_storage: {e}")
        return False

    return True


def test_cloudinary_config():
    """Test if Cloudinary SDK is configured correctly."""
    print("\n" + "=" * 60)
    print("CLOUDINARY SDK CONFIGURATION TEST")
    print("=" * 60)

    try:
        import cloudinary
        import cloudinary.api

        # Check if cloudinary is configured
        if cloudinary.config().cloud_name:
            print(f"[OK] Cloudinary SDK configured")
            print(f"  Cloud Name: {cloudinary.config().cloud_name}")
            print(f"  API Key: {cloudinary.config().api_key}")
            api_secret = cloudinary.config().api_secret
            if api_secret:
                masked = api_secret[:4] + '*' * (len(api_secret) - 8) + api_secret[-4:]
                print(f"  API Secret: {masked}")
            return True
        else:
            print(f"[X] Cloudinary SDK not configured")
            print(f"  Cloud Name: {cloudinary.config().cloud_name}")
            print(f"  API Key: {cloudinary.config().api_key}")
            print(f"  API Secret: {'SET' if cloudinary.config().api_secret else 'NOT SET'}")
            return False

    except Exception as e:
        print(f"[X] Error checking Cloudinary configuration: {e}")
        return False


def test_cloudinary_connection():
    """Test actual connection to Cloudinary API."""
    print("\n" + "=" * 60)
    print("CLOUDINARY API CONNECTION TEST")
    print("=" * 60)

    try:
        import cloudinary
        import cloudinary.api

        # Try to ping Cloudinary API
        print("Attempting to connect to Cloudinary API...")
        response = cloudinary.api.ping()
        print(f"[OK] Successfully connected to Cloudinary!")
        print(f"  Response: {response}")
        return True

    except cloudinary.api.AuthorizationRequired as e:
        print(f"[X] Authorization failed - invalid credentials")
        print(f"  Error: {e}")
        return False
    except cloudinary.api.NotFound as e:
        print(f"[X] Cloud name not found")
        print(f"  Error: {e}")
        return False
    except Exception as e:
        print(f"[X] Failed to connect to Cloudinary")
        print(f"  Error type: {type(e).__name__}")
        print(f"  Error: {e}")
        return False


def test_django_storage():
    """Test Django storage backend configuration."""
    print("\n" + "=" * 60)
    print("DJANGO STORAGE BACKEND TEST")
    print("=" * 60)

    try:
        # Setup Django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        import django
        django.setup()

        from django.conf import settings
        from django.core.files.storage import default_storage

        print(f"Default storage backend: {default_storage.__class__.__name__}")
        print(f"  Module: {default_storage.__class__.__module__}")

        if 'cloudinary' in str(default_storage.__class__).lower():
            print(f"[OK] Using Cloudinary storage backend")
            return True
        else:
            print(f"[!] Not using Cloudinary storage backend")
            print(f"  Check STORAGES configuration in settings.py")
            return False

    except Exception as e:
        print(f"[X] Error checking Django storage: {e}")
        print(f"  Error type: {type(e).__name__}")
        return False


def main():
    """Run all diagnostic tests."""
    print("\n" + "=" * 60)
    print("CLOUDINARY DIAGNOSTIC TESTS")
    print("=" * 60)
    print()

    results = []

    # Test 1: Environment variables
    results.append(("Environment Variables", test_cloudinary_env_vars()))

    # Test 2: Package imports
    results.append(("Package Imports", test_cloudinary_import()))

    # Test 3: SDK configuration
    results.append(("SDK Configuration", test_cloudinary_config()))

    # Test 4: API connection
    results.append(("API Connection", test_cloudinary_connection()))

    # Test 5: Django storage
    results.append(("Django Storage", test_django_storage()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, result in results:
        status = "[OK] PASS" if result else "[X] FAIL"
        print(f"{test_name}: {status}")

    passed = sum(1 for _, result in results if result)
    print(f"\nTotal: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\n[OK] All tests passed! Cloudinary is configured correctly.")
        print("  Avatar upload should work. Check application logs for other issues.")
        return 0
    else:
        print("\n[X] Some tests failed. Fix the issues above before avatar upload will work.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
