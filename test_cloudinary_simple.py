"""
Simple Cloudinary credential checker.
Shows what Django sees (with partial masking).
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings

print("=" * 60)
print("CLOUDINARY CREDENTIALS DEBUG")
print("=" * 60)

cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '')
api_key = os.environ.get('CLOUDINARY_API_KEY', '')
api_secret = os.environ.get('CLOUDINARY_API_SECRET', '')

# Mask credentials for security (show first/last few chars)
def mask(value, show_chars=4):
    if not value:
        return '[NOT SET]'
    if len(value) <= show_chars * 2:
        return '*' * len(value)
    return f"{value[:show_chars]}...{value[-show_chars:]}"

print(f"\nEnvironment Variables:")
print(f"  CLOUDINARY_CLOUD_NAME: {cloud_name}")
print(f"  CLOUDINARY_API_KEY:    {mask(api_key)}")
print(f"  CLOUDINARY_API_SECRET: {mask(api_secret)}")

print(f"\nActual lengths:")
print(f"  Cloud Name: {len(cloud_name)} chars")
print(f"  API Key:    {len(api_key)} chars")
print(f"  API Secret: {len(api_secret)} chars")

# Check for common issues
issues = []
if ' ' in cloud_name:
    issues.append("Cloud name contains spaces!")
if ' ' in api_key:
    issues.append("API key contains spaces!")
if ' ' in api_secret:
    issues.append("API secret contains spaces!")

if cloud_name != cloud_name.strip():
    issues.append("Cloud name has leading/trailing whitespace!")
if api_key != api_key.strip():
    issues.append("API key has leading/trailing whitespace!")
if api_secret != api_secret.strip():
    issues.append("API secret has leading/trailing whitespace!")

if issues:
    print(f"\n[!] ISSUES FOUND:")
    for issue in issues:
        print(f"    - {issue}")
else:
    print(f"\n[OK] No obvious issues with credential format")

print("\nCloudinary apps in INSTALLED_APPS:")
print(f"  cloudinary_storage: {'YES' if 'cloudinary_storage' in settings.INSTALLED_APPS else 'NO'}")
print(f"  cloudinary:         {'YES' if 'cloudinary' in settings.INSTALLED_APPS else 'NO'}")

print("=" * 60)
