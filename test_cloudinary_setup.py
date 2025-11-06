"""
Test script to verify Cloudinary is configured and working correctly.

Usage:
    python test_cloudinary_setup.py
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def test_cloudinary_configuration():
    """Test that Cloudinary environment variables are set."""
    print("=" * 60)
    print("CLOUDINARY CONFIGURATION TEST")
    print("=" * 60)

    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
    api_key = os.environ.get('CLOUDINARY_API_KEY')
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')

    print("\n1. Environment Variables Check:")
    print(f"   CLOUDINARY_CLOUD_NAME: {'[OK] Set' if cloud_name else '[X] NOT SET'}")
    print(f"   CLOUDINARY_API_KEY:    {'[OK] Set' if api_key else '[X] NOT SET'}")
    print(f"   CLOUDINARY_API_SECRET: {'[OK] Set' if api_secret else '[X] NOT SET'}")

    if not all([cloud_name, api_key, api_secret]):
        print("\n[ERROR] Cloudinary environment variables are not set!")
        print("\nTo fix, run these commands:")
        print('   export CLOUDINARY_CLOUD_NAME="your_cloud_name"')
        print('   export CLOUDINARY_API_KEY="your_api_key"')
        print('   export CLOUDINARY_API_SECRET="your_api_secret"')
        return False

    return True

def test_cloudinary_in_installed_apps():
    """Test that Cloudinary apps are in INSTALLED_APPS."""
    from django.conf import settings

    print("\n2. Django INSTALLED_APPS Check:")
    has_cloudinary_storage = 'cloudinary_storage' in settings.INSTALLED_APPS
    has_cloudinary = 'cloudinary' in settings.INSTALLED_APPS

    print(f"   cloudinary_storage: {'[OK] Loaded' if has_cloudinary_storage else '[X] NOT loaded'}")
    print(f"   cloudinary:         {'[OK] Loaded' if has_cloudinary else '[X] NOT loaded'}")

    if not has_cloudinary_storage or not has_cloudinary:
        print("\n[!] WARNING: Cloudinary apps not in INSTALLED_APPS")
        print("   This means Cloudinary env vars are not set.")
        return False

    return True

def test_storage_backend():
    """Test that the correct storage backend is configured."""
    from django.conf import settings

    print("\n3. Storage Backend Check:")
    default_storage = settings.STORAGES.get('default', {}).get('BACKEND', 'Not set')

    print(f"   Storage backend: {default_storage}")

    if 'cloudinary' in default_storage.lower():
        print("   [OK] Using Cloudinary storage")
        return True
    else:
        print("   [!] Using filesystem storage (Cloudinary not active)")
        return False

def test_cloudinary_connection():
    """Test actual connection to Cloudinary."""
    print("\n4. Cloudinary Connection Test:")

    try:
        import cloudinary
        import cloudinary.api

        # Try to get account details (lightweight API call)
        result = cloudinary.api.ping()

        print(f"   [OK] Successfully connected to Cloudinary!")
        print(f"   Status: {result.get('status', 'unknown')}")
        return True

    except ImportError:
        print("   [X] Cloudinary package not installed")
        print("   Run: pip install cloudinary==1.41.0 django-cloudinary-storage==0.3.0")
        return False
    except Exception as e:
        print(f"   [X] Connection failed: {str(e)}")
        print("   Check your credentials are correct")
        return False

def main():
    """Run all Cloudinary tests."""
    tests = [
        test_cloudinary_configuration(),
        test_cloudinary_in_installed_apps(),
        test_storage_backend(),
        test_cloudinary_connection(),
    ]

    print("\n" + "=" * 60)
    if all(tests):
        print("[SUCCESS] ALL TESTS PASSED - Cloudinary is configured correctly!")
    else:
        print("[FAILED] SOME TESTS FAILED - Check the output above for issues")
    print("=" * 60)

    return all(tests)

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
