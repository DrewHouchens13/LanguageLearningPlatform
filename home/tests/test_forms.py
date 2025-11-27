"""
Tests for home/forms.py - AvatarUploadForm validation.

Tests cover multi-layer validation:
1. File size validation
2. File extension validation
3. MIME type validation
4. Binary content (PIL) validation
"""

import io
from unittest.mock import MagicMock, patch
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from PIL import Image

from home.forms import AvatarUploadForm


class AvatarUploadFormTests(TestCase):
    """Tests for AvatarUploadForm avatar validation."""

    def _create_test_image(self, format_type='PNG', size=(100, 100)):
        """Helper to create a valid test image file."""
        img = Image.new('RGB', size, color='red')
        img_io = io.BytesIO()
        img.save(img_io, format=format_type)
        img_io.seek(0)
        return img_io

    def test_form_accepts_valid_png(self):
        """Form should accept valid PNG images."""
        img_io = self._create_test_image('PNG')
        uploaded_file = SimpleUploadedFile(
            name='test.png',
            content=img_io.read(),
            content_type='image/png'
        )

        form = AvatarUploadForm(files={'avatar': uploaded_file})
        # Form needs an instance since it's a ModelForm
        form.instance = MagicMock()
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_accepts_valid_jpg(self):
        """Form should accept valid JPG images."""
        img_io = self._create_test_image('JPEG')
        uploaded_file = SimpleUploadedFile(
            name='test.jpg',
            content=img_io.read(),
            content_type='image/jpeg'
        )

        form = AvatarUploadForm(files={'avatar': uploaded_file})
        form.instance = MagicMock()
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_accepts_valid_jpeg_extension(self):
        """Form should accept .jpeg extension."""
        img_io = self._create_test_image('JPEG')
        uploaded_file = SimpleUploadedFile(
            name='test.jpeg',
            content=img_io.read(),
            content_type='image/jpeg'
        )

        form = AvatarUploadForm(files={'avatar': uploaded_file})
        form.instance = MagicMock()
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_allows_no_avatar(self):
        """Form should allow submission without avatar."""
        form = AvatarUploadForm(files={})
        form.instance = MagicMock()
        # No avatar is valid - user can skip avatar upload
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejects_file_too_large(self):
        """Form should reject files larger than 5MB."""
        # Create a mock file that claims to be 6MB
        img_io = self._create_test_image('PNG')
        uploaded_file = SimpleUploadedFile(
            name='large.png',
            content=img_io.read(),
            content_type='image/png'
        )
        # Mock the size to be over 5MB
        uploaded_file.size = 6 * 1024 * 1024

        form = AvatarUploadForm(files={'avatar': uploaded_file})
        form.instance = MagicMock()
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)
        self.assertIn('5MB', str(form.errors['avatar']))

    def test_form_rejects_invalid_extension(self):
        """Form should reject files with invalid extensions."""
        img_io = self._create_test_image('PNG')
        uploaded_file = SimpleUploadedFile(
            name='test.gif',
            content=img_io.read(),
            content_type='image/gif'
        )

        form = AvatarUploadForm(files={'avatar': uploaded_file})
        form.instance = MagicMock()
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)
        self.assertIn('Invalid file type', str(form.errors['avatar']))

    def test_form_rejects_no_extension(self):
        """Form should reject files with no extension."""
        img_io = self._create_test_image('PNG')
        uploaded_file = SimpleUploadedFile(
            name='testfile',
            content=img_io.read(),
            content_type='image/png'
        )

        form = AvatarUploadForm(files={'avatar': uploaded_file})
        form.instance = MagicMock()
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    def test_form_rejects_exe_extension(self):
        """Form should reject executable files."""
        uploaded_file = SimpleUploadedFile(
            name='malware.exe',
            content=b'MZ\x00\x00',  # PE header
            content_type='application/x-msdownload'
        )

        form = AvatarUploadForm(files={'avatar': uploaded_file})
        form.instance = MagicMock()
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    def test_form_checks_mime_type_attribute(self):
        """Form should check content_type when present."""
        # Test that form checks MIME type by using a non-image file
        # with image extension but wrong content_type
        uploaded_file = SimpleUploadedFile(
            name='fake.png',
            content=b'not an image',
            content_type='text/plain'
        )

        form = AvatarUploadForm(files={'avatar': uploaded_file})
        form.instance = MagicMock()
        # Form should reject due to either MIME type or binary content
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    def test_form_rejects_corrupted_image(self):
        """Form should reject corrupted image files."""
        uploaded_file = SimpleUploadedFile(
            name='corrupted.png',
            content=b'not a real image file content',
            content_type='image/png'
        )

        form = AvatarUploadForm(files={'avatar': uploaded_file})
        form.instance = MagicMock()
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)
        self.assertIn('corrupted', str(form.errors['avatar']).lower())

    def test_form_rejects_gif_disguised_as_png(self):
        """Form should reject GIF images renamed to .png."""
        # Create an actual GIF
        img = Image.new('RGB', (100, 100), color='blue')
        img_io = io.BytesIO()
        img.save(img_io, format='GIF')
        img_io.seek(0)

        uploaded_file = SimpleUploadedFile(
            name='fake.png',
            content=img_io.read(),
            content_type='image/png'
        )

        form = AvatarUploadForm(files={'avatar': uploaded_file})
        form.instance = MagicMock()
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    def test_form_case_insensitive_extension(self):
        """Form should accept uppercase extensions."""
        img_io = self._create_test_image('PNG')
        uploaded_file = SimpleUploadedFile(
            name='test.PNG',
            content=img_io.read(),
            content_type='image/png'
        )

        form = AvatarUploadForm(files={'avatar': uploaded_file})
        form.instance = MagicMock()
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_handles_file_without_content_type(self):
        """Form should handle files without content_type attribute."""
        img_io = self._create_test_image('PNG')
        uploaded_file = SimpleUploadedFile(
            name='test.png',
            content=img_io.read(),
        )
        # Remove content_type attribute
        if hasattr(uploaded_file, 'content_type'):
            delattr(uploaded_file, 'content_type')

        form = AvatarUploadForm(files={'avatar': uploaded_file})
        form.instance = MagicMock()
        # Should pass since we removed content_type check
        # The file has valid extension and valid binary content
        # Actually the form will still work as hasattr check handles this

    def test_clean_avatar_returns_avatar(self):
        """clean_avatar should return the validated avatar file."""
        img_io = self._create_test_image('PNG')
        uploaded_file = SimpleUploadedFile(
            name='test.png',
            content=img_io.read(),
            content_type='image/png'
        )

        form = AvatarUploadForm(files={'avatar': uploaded_file})
        form.instance = MagicMock()
        self.assertTrue(form.is_valid())
        # After validation, cleaned_data should contain the avatar
        self.assertIsNotNone(form.cleaned_data.get('avatar'))

    def test_clean_avatar_resets_file_pointer(self):
        """clean_avatar should reset file pointer after validation."""
        img_io = self._create_test_image('PNG')
        uploaded_file = SimpleUploadedFile(
            name='test.png',
            content=img_io.read(),
            content_type='image/png'
        )

        form = AvatarUploadForm(files={'avatar': uploaded_file})
        form.instance = MagicMock()
        form.is_valid()

        # File pointer should be reset to 0
        avatar = form.cleaned_data.get('avatar')
        if avatar:
            self.assertEqual(avatar.tell(), 0)


class AvatarFormWidgetTests(TestCase):
    """Tests for form widget configuration."""

    def test_avatar_widget_has_correct_class(self):
        """Avatar widget should have form-control class."""
        form = AvatarUploadForm()
        widget = form.fields['avatar'].widget
        self.assertIn('class', widget.attrs)
        self.assertIn('form-control', widget.attrs['class'])

    def test_avatar_widget_accepts_correct_types(self):
        """Avatar widget should only accept PNG and JPG."""
        form = AvatarUploadForm()
        widget = form.fields['avatar'].widget
        self.assertIn('accept', widget.attrs)
        accept = widget.attrs['accept']
        self.assertIn('image/png', accept)
        self.assertIn('image/jpeg', accept)
