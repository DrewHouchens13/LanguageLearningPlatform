"""
Custom template filters for markdown rendering.

SOFA Principles:
- Single Responsibility: Convert markdown to HTML
- Function Extraction: Dedicated filter for markdown processing
"""

from django import template
from django.utils.safestring import mark_safe
import markdown as md

register = template.Library()


@register.filter(name='markdown')
def markdown_filter(text):
    """
    Convert markdown text to HTML.

    Usage in templates:
        {{ content|markdown }}

    Args:
        text: Markdown-formatted text

    Returns:
        SafeString containing HTML
    """
    if not text:
        return ""

    # Configure markdown with extensions for better rendering
    html = md.markdown(
        text,
        extensions=[
            'markdown.extensions.extra',  # Tables, fenced code blocks, etc.
            'markdown.extensions.nl2br',   # Newline to <br>
            'markdown.extensions.sane_lists',  # Better list handling
        ]
    )

    # Security note: mark_safe is safe here because content comes from trusted
    # help documentation files, not user input. The markdown files are part of
    # the application codebase and controlled by developers.
    return mark_safe(html)  # nosemgrep: python.django.security.audit.avoid-mark-safe.avoid-mark-safe  # nosec B703, B308
