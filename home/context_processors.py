"""
Context processors for the home app.

Context processors add variables to all template contexts automatically.
"""
from django.conf import settings


def app_version(request):
    """
    Add application version information to all template contexts.

    Variables added:
    - app_version: The current application version string
    - show_version: Boolean indicating whether version should be displayed

    Security: In production, set SHOW_VERSION=False environment variable
    to hide version information and prevent version disclosure attacks.
    """
    return {
        'app_version': settings.APP_VERSION,
        'show_version': settings.SHOW_VERSION,
    }
