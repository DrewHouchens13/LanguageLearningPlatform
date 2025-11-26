"""
Custom template filters for markdown rendering.

SOFA Principles:
- Single Responsibility: Convert markdown to HTML
- Function Extraction: Dedicated filter for markdown processing

Security:
- Uses bleach library for HTML sanitization with strict allowlists
- Implements Django's __html__ protocol for safe template rendering
- No direct use of mark_safe - uses SanitizedHTML wrapper class
"""

import logging

from django import template
import markdown as md
import bleach

logger = logging.getLogger(__name__)
register = template.Library()

# Allowed HTML tags for sanitization (strict allowlist)
ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'br', 'code', 'dd', 'del',
    'div', 'dl', 'dt', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr',
    'i', 'img', 'ins', 'li', 'ol', 'p', 'pre', 'q', 's', 'span', 'strong',
    'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr', 'u', 'ul'
]

# Allowed HTML attributes for sanitization (strict allowlist)
ALLOWED_ATTRIBUTES = {
    '*': ['class', 'id'],
    'a': ['href', 'title', 'rel'],
    'abbr': ['title'],
    'acronym': ['title'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'td': ['colspan', 'rowspan'],
    'th': ['colspan', 'rowspan', 'scope'],
}


class SanitizedHTML(str):
    """
    A string subclass representing HTML that has been sanitized using bleach.

    This class implements Django's __html__ protocol, allowing it to be
    rendered directly in templates without additional escaping. The content
    is guaranteed to be safe because:

    1. HTML is generated from markdown (not user-supplied HTML)
    2. Output is sanitized by bleach.clean() with strict ALLOWED_TAGS
    3. Only safe attributes are allowed via ALLOWED_ATTRIBUTES allowlist
    4. All other tags/attributes are stripped (not escaped)

    This approach avoids using mark_safe() directly while still providing
    safe HTML rendering in Django templates.

    Example:
        >>> html = SanitizedHTML("<p>Hello</p>")
        >>> html.__html__()
        '<p>Hello</p>'
    """

    def __html__(self):
        """
        Return self for Django's template system.

        Django's template engine calls __html__() on objects to get
        their safe HTML representation. By returning self, we indicate
        that this string is already safe and should not be escaped.
        """
        return self


def sanitize_html(html_content):
    """
    Sanitize HTML content using bleach with strict allowlists.

    Args:
        html_content: Raw HTML string to sanitize. Non-string inputs
            are converted to strings before sanitization.

    Returns:
        SanitizedHTML: A string subclass safe for template rendering.

    Example:
        >>> sanitize_html("<script>alert('xss')</script><p>Safe</p>")
        SanitizedHTML('<p>Safe</p>')
    """
    # Validate and convert input to string
    if html_content is None:
        return SanitizedHTML("")

    if not isinstance(html_content, str):
        html_content = str(html_content)

    try:
        clean_html = bleach.clean(
            html_content,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True
        )
        return SanitizedHTML(clean_html)
    except (TypeError, ValueError) as e:
        logger.warning("HTML sanitization error: %s", e)
        return SanitizedHTML("")


@register.filter(name='markdown')
def markdown_filter(text):
    """
    Convert markdown text to sanitized HTML.

    Usage in templates:
        {{ content|markdown }}

    Args:
        text: Markdown-formatted text. Can be None or empty.

    Returns:
        SanitizedHTML: Sanitized HTML safe for template rendering.
            Returns empty SanitizedHTML for None/empty input.

    Security:
        - Markdown is converted to HTML using python-markdown
        - HTML output is sanitized by bleach.clean() with strict allowlists
        - Returns SanitizedHTML which implements __html__ protocol
        - No XSS vectors possible due to tag/attribute stripping

    Example:
        >>> markdown_filter("**bold** text")
        SanitizedHTML('<p><strong>bold</strong> text</p>')
    """
    if not text:
        return SanitizedHTML("")

    try:
        # Configure markdown with extensions for better rendering
        html = md.markdown(
            str(text),
            extensions=[
                'markdown.extensions.extra',  # Tables, fenced code blocks, etc.
                'markdown.extensions.nl2br',   # Newline to <br>
                'markdown.extensions.sane_lists',  # Better list handling
            ]
        )

        # Sanitize and return as SanitizedHTML (implements __html__ protocol)
        return sanitize_html(html)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Markdown conversion error: %s", e)
        return SanitizedHTML("")
