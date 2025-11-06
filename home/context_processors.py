"""
Context processors for making variables available to all templates.
"""
from django.conf import settings


def devedu_context(request):
    """
    Add IS_DEVEDU flag to template context.

    This allows templates to conditionally include DevEDU-specific fixes
    (like HTML base tags) without affecting other environments.
    """
    return {
        'IS_DEVEDU': settings.IS_DEVEDU
    }
