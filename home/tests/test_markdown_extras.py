"""
Tests for markdown_extras template tags.

Tests the SanitizedHTML class, sanitize_html function, and markdown_filter
template filter with comprehensive edge case coverage.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase

from home.templatetags.markdown_extras import (
    SanitizedHTML,
    sanitize_html,
    markdown_filter,
    ALLOWED_TAGS,
    ALLOWED_ATTRIBUTES,
)


class SanitizedHTMLTests(TestCase):
    """Tests for the SanitizedHTML class."""

    def test_sanitized_html_is_string_subclass(self):
        """SanitizedHTML should be a subclass of str."""
        html = SanitizedHTML("<p>test</p>")
        self.assertIsInstance(html, str)

    def test_sanitized_html_preserves_content(self):
        """SanitizedHTML should preserve the HTML content."""
        content = "<p>Hello World</p>"
        html = SanitizedHTML(content)
        self.assertEqual(html, content)

    def test_sanitized_html_html_method_returns_self(self):
        """__html__() method should return self for Django template system."""
        content = "<p>test</p>"
        html = SanitizedHTML(content)
        self.assertEqual(html.__html__(), html)
        self.assertIs(html.__html__(), html)

    def test_sanitized_html_empty_string(self):
        """SanitizedHTML should handle empty strings."""
        html = SanitizedHTML("")
        self.assertEqual(html, "")
        self.assertEqual(html.__html__(), "")

    def test_sanitized_html_with_special_characters(self):
        """SanitizedHTML should preserve special characters."""
        content = "<p>&amp; &lt; &gt; &quot;</p>"
        html = SanitizedHTML(content)
        self.assertEqual(html, content)


class SanitizeHTMLTests(TestCase):
    """Tests for the sanitize_html function."""

    def test_sanitize_html_returns_sanitized_html_type(self):
        """sanitize_html should return a SanitizedHTML instance."""
        result = sanitize_html("<p>test</p>")
        self.assertIsInstance(result, SanitizedHTML)

    def test_sanitize_html_preserves_allowed_tags(self):
        """sanitize_html should preserve allowed HTML tags."""
        html = "<p>paragraph</p><strong>bold</strong><em>italic</em>"
        result = sanitize_html(html)
        self.assertIn("<p>", result)
        self.assertIn("<strong>", result)
        self.assertIn("<em>", result)

    def test_sanitize_html_strips_disallowed_tags(self):
        """sanitize_html should strip disallowed HTML tags."""
        html = "<script>alert('xss')</script><p>safe</p>"
        result = sanitize_html(html)
        # Script tags are stripped, content may remain but is harmless text
        self.assertNotIn("<script>", result)
        self.assertNotIn("</script>", result)
        self.assertIn("<p>safe</p>", result)

    def test_sanitize_html_strips_onclick_attribute(self):
        """sanitize_html should strip dangerous attributes like onclick."""
        html = '<p onclick="alert(1)">text</p>'
        result = sanitize_html(html)
        self.assertNotIn("onclick", result)
        self.assertIn("<p>text</p>", result)

    def test_sanitize_html_preserves_allowed_attributes(self):
        """sanitize_html should preserve allowed attributes."""
        html = '<a href="https://example.com" title="Link">click</a>'
        result = sanitize_html(html)
        self.assertIn('href="https://example.com"', result)
        self.assertIn('title="Link"', result)

    def test_sanitize_html_with_none_input(self):
        """sanitize_html should return empty SanitizedHTML for None input."""
        result = sanitize_html(None)
        self.assertIsInstance(result, SanitizedHTML)
        self.assertEqual(result, "")

    def test_sanitize_html_with_integer_input(self):
        """sanitize_html should convert non-string input to string."""
        result = sanitize_html(12345)
        self.assertIsInstance(result, SanitizedHTML)
        self.assertEqual(result, "12345")

    def test_sanitize_html_with_float_input(self):
        """sanitize_html should convert float input to string."""
        result = sanitize_html(3.14159)
        self.assertIsInstance(result, SanitizedHTML)
        self.assertIn("3.14", result)

    def test_sanitize_html_with_list_input(self):
        """sanitize_html should convert list input to string."""
        result = sanitize_html(['item1', 'item2'])
        self.assertIsInstance(result, SanitizedHTML)
        # List str representation contains brackets
        self.assertIn("item1", result)

    def test_sanitize_html_with_empty_string(self):
        """sanitize_html should handle empty string input."""
        result = sanitize_html("")
        self.assertIsInstance(result, SanitizedHTML)
        self.assertEqual(result, "")

    def test_sanitize_html_strips_style_tag(self):
        """sanitize_html should strip style tags."""
        html = "<style>body{color:red}</style><p>text</p>"
        result = sanitize_html(html)
        self.assertNotIn("<style>", result)
        self.assertIn("<p>text</p>", result)

    def test_sanitize_html_strips_iframe_tag(self):
        """sanitize_html should strip iframe tags."""
        html = '<iframe src="evil.com"></iframe><p>safe</p>'
        result = sanitize_html(html)
        self.assertNotIn("<iframe>", result)
        self.assertIn("<p>safe</p>", result)

    def test_sanitize_html_preserves_table_structure(self):
        """sanitize_html should preserve table tags."""
        html = "<table><tr><td>cell</td></tr></table>"
        result = sanitize_html(html)
        self.assertIn("<table>", result)
        self.assertIn("<tr>", result)
        self.assertIn("<td>", result)

    def test_sanitize_html_preserves_image_with_allowed_attrs(self):
        """sanitize_html should preserve img tags with allowed attributes."""
        html = '<img src="image.png" alt="description" width="100">'
        result = sanitize_html(html)
        self.assertIn("<img", result)
        self.assertIn('src="image.png"', result)
        self.assertIn('alt="description"', result)

    @patch('home.templatetags.markdown_extras.bleach.clean')
    def test_sanitize_html_handles_bleach_error(self, mock_clean):
        """sanitize_html should handle bleach errors gracefully."""
        mock_clean.side_effect = TypeError("Bleach error")
        result = sanitize_html("<p>test</p>")
        self.assertIsInstance(result, SanitizedHTML)
        self.assertEqual(result, "")

    @patch('home.templatetags.markdown_extras.bleach.clean')
    def test_sanitize_html_handles_value_error(self, mock_clean):
        """sanitize_html should handle ValueError gracefully."""
        mock_clean.side_effect = ValueError("Invalid value")
        result = sanitize_html("<p>test</p>")
        self.assertIsInstance(result, SanitizedHTML)
        self.assertEqual(result, "")


class MarkdownFilterTests(TestCase):
    """Tests for the markdown_filter template filter."""

    def test_markdown_filter_returns_sanitized_html_type(self):
        """markdown_filter should return a SanitizedHTML instance."""
        result = markdown_filter("**bold**")
        self.assertIsInstance(result, SanitizedHTML)

    def test_markdown_filter_converts_bold(self):
        """markdown_filter should convert **text** to strong tags."""
        result = markdown_filter("**bold text**")
        self.assertIn("<strong>", result)
        self.assertIn("bold text", result)

    def test_markdown_filter_converts_italic(self):
        """markdown_filter should convert *text* to em tags."""
        result = markdown_filter("*italic text*")
        self.assertIn("<em>", result)
        self.assertIn("italic text", result)

    def test_markdown_filter_converts_headers(self):
        """markdown_filter should convert # headers."""
        result = markdown_filter("# Header 1")
        self.assertIn("<h1>", result)
        self.assertIn("Header 1", result)

    def test_markdown_filter_converts_links(self):
        """markdown_filter should convert [text](url) to links."""
        result = markdown_filter("[Click here](https://example.com)")
        self.assertIn("<a", result)
        self.assertIn("https://example.com", result)
        self.assertIn("Click here", result)

    def test_markdown_filter_converts_lists(self):
        """markdown_filter should convert markdown lists."""
        result = markdown_filter("- item 1\n- item 2")
        self.assertIn("<ul>", result)
        self.assertIn("<li>", result)

    def test_markdown_filter_converts_code_blocks(self):
        """markdown_filter should convert code blocks."""
        result = markdown_filter("```\ncode\n```")
        self.assertIn("<code>", result)

    def test_markdown_filter_converts_inline_code(self):
        """markdown_filter should convert `inline code`."""
        result = markdown_filter("`inline code`")
        self.assertIn("<code>", result)
        self.assertIn("inline code", result)

    def test_markdown_filter_with_empty_string(self):
        """markdown_filter should return empty SanitizedHTML for empty input."""
        result = markdown_filter("")
        self.assertIsInstance(result, SanitizedHTML)
        self.assertEqual(result, "")

    def test_markdown_filter_with_none_input(self):
        """markdown_filter should return empty SanitizedHTML for None input."""
        result = markdown_filter(None)
        self.assertIsInstance(result, SanitizedHTML)
        self.assertEqual(result, "")

    def test_markdown_filter_with_whitespace_only(self):
        """markdown_filter should handle whitespace-only input."""
        result = markdown_filter("   ")
        # Whitespace is truthy, so it goes through markdown processing
        self.assertIsInstance(result, SanitizedHTML)

    def test_markdown_filter_sanitizes_script_in_markdown(self):
        """markdown_filter should sanitize any script tags in output."""
        # Markdown that might produce script tags
        result = markdown_filter("<script>alert('xss')</script>")
        # Script tags are stripped - the key is no executable script tags remain
        self.assertNotIn("<script>", result)
        self.assertNotIn("</script>", result)

    def test_markdown_filter_with_integer_input(self):
        """markdown_filter should handle integer input."""
        result = markdown_filter(42)
        self.assertIsInstance(result, SanitizedHTML)
        self.assertIn("42", result)

    def test_markdown_filter_converts_newlines_to_br(self):
        """markdown_filter should convert newlines to br tags (nl2br extension)."""
        result = markdown_filter("line1\nline2")
        self.assertIn("<br", result)

    def test_markdown_filter_converts_tables(self):
        """markdown_filter should convert markdown tables."""
        table_md = "| Header |\n|--------|\n| Cell   |"
        result = markdown_filter(table_md)
        self.assertIn("<table>", result)
        self.assertIn("<th>", result)
        self.assertIn("<td>", result)

    @patch('home.templatetags.markdown_extras.md.markdown')
    def test_markdown_filter_handles_markdown_error(self, mock_markdown):
        """markdown_filter should handle markdown conversion errors."""
        mock_markdown.side_effect = Exception("Markdown error")
        result = markdown_filter("**test**")
        self.assertIsInstance(result, SanitizedHTML)
        self.assertEqual(result, "")

    @patch('home.templatetags.markdown_extras.md.markdown')
    def test_markdown_filter_logs_error_on_exception(self, mock_markdown):
        """markdown_filter should log errors when exceptions occur."""
        mock_markdown.side_effect = Exception("Markdown error")
        with patch('home.templatetags.markdown_extras.logger') as mock_logger:
            markdown_filter("**test**")
            mock_logger.error.assert_called_once()


class AllowlistConfigurationTests(TestCase):
    """Tests to verify allowlist configuration."""

    def test_allowed_tags_contains_common_tags(self):
        """ALLOWED_TAGS should contain common HTML tags."""
        expected_tags = ['p', 'a', 'strong', 'em', 'code', 'pre', 'ul', 'ol', 'li']
        for tag in expected_tags:
            self.assertIn(tag, ALLOWED_TAGS)

    def test_allowed_tags_contains_header_tags(self):
        """ALLOWED_TAGS should contain all header tags."""
        for i in range(1, 7):
            self.assertIn(f'h{i}', ALLOWED_TAGS)

    def test_allowed_tags_contains_table_tags(self):
        """ALLOWED_TAGS should contain table-related tags."""
        table_tags = ['table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td']
        for tag in table_tags:
            self.assertIn(tag, ALLOWED_TAGS)

    def test_allowed_tags_excludes_dangerous_tags(self):
        """ALLOWED_TAGS should NOT contain dangerous tags."""
        dangerous_tags = ['script', 'style', 'iframe', 'object', 'embed', 'form']
        for tag in dangerous_tags:
            self.assertNotIn(tag, ALLOWED_TAGS)

    def test_allowed_attributes_for_links(self):
        """ALLOWED_ATTRIBUTES should allow href and title for links."""
        self.assertIn('a', ALLOWED_ATTRIBUTES)
        self.assertIn('href', ALLOWED_ATTRIBUTES['a'])
        self.assertIn('title', ALLOWED_ATTRIBUTES['a'])

    def test_allowed_attributes_for_images(self):
        """ALLOWED_ATTRIBUTES should allow src, alt for images."""
        self.assertIn('img', ALLOWED_ATTRIBUTES)
        self.assertIn('src', ALLOWED_ATTRIBUTES['img'])
        self.assertIn('alt', ALLOWED_ATTRIBUTES['img'])

    def test_allowed_attributes_global_class_and_id(self):
        """ALLOWED_ATTRIBUTES should allow class and id globally."""
        self.assertIn('*', ALLOWED_ATTRIBUTES)
        self.assertIn('class', ALLOWED_ATTRIBUTES['*'])
        self.assertIn('id', ALLOWED_ATTRIBUTES['*'])


class IntegrationTests(TestCase):
    """Integration tests for markdown rendering pipeline."""

    def test_full_markdown_document(self):
        """Test rendering a full markdown document."""
        markdown_doc = """
# Welcome

This is a **test** document with *formatting*.

## Features

- Item 1
- Item 2

[Link](https://example.com)

| Header |
|--------|
| Cell   |
"""
        result = markdown_filter(markdown_doc)
        self.assertIsInstance(result, SanitizedHTML)
        self.assertIn("<h1>", result)
        self.assertIn("<h2>", result)
        self.assertIn("<strong>", result)
        self.assertIn("<em>", result)
        self.assertIn("<ul>", result)
        self.assertIn("<a", result)
        self.assertIn("<table>", result)

    def test_xss_prevention_in_markdown(self):
        """Test that XSS attempts are prevented in markdown."""
        # Test script tags are stripped
        result = markdown_filter('<script>alert("xss")</script>')
        self.assertNotIn("<script>", result)
        self.assertNotIn("</script>", result)

        # Test dangerous attributes are stripped
        result = markdown_filter('<img src="x" onerror="alert(1)">')
        self.assertNotIn("onerror", result)

        # Test javascript: URLs are stripped
        result = markdown_filter('<a href="javascript:alert(1)">click</a>')
        self.assertNotIn("javascript:", result)

        # Test event handlers are stripped
        result = markdown_filter('<div onmouseover="alert(1)">hover</div>')
        self.assertNotIn("onmouseover", result)
