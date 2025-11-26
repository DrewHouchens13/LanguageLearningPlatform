"""
Custom template filters for markdown rendering.

SOFA Principles:
- Single Responsibility: Convert markdown to HTML
- Function Extraction: Dedicated filter for markdown processing
"""

from django import template
from django.utils.safestring import mark_safe
import markdown as md
import bleach

register = template.Library()

# Allowed HTML tags and attributes for sanitization
ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'br', 'code', 'dd', 'del',
    'div', 'dl', 'dt', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr',
    'i', 'img', 'ins', 'li', 'ol', 'p', 'pre', 'q', 's', 'span', 'strong',
    'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr', 'u', 'ul'
]

ALLOWED_ATTRIBUTES = {
    '*': ['class', 'id'],
    'a': ['href', 'title', 'rel'],
    'abbr': ['title'],
    'acronym': ['title'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan', 'scope'],
}


@register.filter(name='markdown')
def markdown_filter(text):
    """
    Convert markdown text to sanitized HTML.

    Usage in templates:
        {{ content|markdown }}

    Args:
        text: Markdown-formatted text

    Returns:
        SafeString containing sanitized HTML
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

    # Sanitize HTML to prevent XSS attacks
    # This allows only safe HTML tags and attributes
    clean_html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )

    return mark_safe(clean_html)
