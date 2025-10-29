"""
Forms for the home app, including user profile avatar upload.
"""
import os
from django import forms
from django.core.exceptions import ValidationError
from .models import UserProfile


class AvatarUploadForm(forms.ModelForm):
    """
    Form for uploading user avatars with validation.

    Validates:
    - File type: Only PNG and JPG allowed
    - File size: Maximum 5MB
    """

    class Meta:
        model = UserProfile
        fields = ['avatar']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/png,image/jpeg,image/jpg',
            })
        }

    def clean_avatar(self):
        """
        Validate avatar upload for file type, MIME type, and size.

        Multi-layer validation prevents malicious file uploads:
        1. File extension check
        2. MIME type validation
        3. File size enforcement (both form and server-side)

        Returns:
            File: The validated avatar file

        Raises:
            ValidationError: If file type, MIME type, or size is invalid
        """
        avatar = self.cleaned_data.get('avatar')

        # Return early if no file uploaded (allows users to skip avatar upload)
        if not avatar:
            return avatar

        # Layer 1: Validate file extension using os.path.splitext for robust parsing
        # This handles edge cases like multiple dots, no extension, etc.
        valid_extensions = ['.png', '.jpg', '.jpeg']
        _, file_extension = os.path.splitext(avatar.name.lower())

        if not file_extension or file_extension not in valid_extensions:
            raise ValidationError(
                'Invalid file type. Only PNG and JPG images are allowed.'
            )

        # Layer 2: Validate MIME type to prevent executable files disguised as images
        # This prevents attacks where malicious files use image extensions
        valid_mime_types = ['image/png', 'image/jpeg', 'image/jpg']
        if hasattr(avatar, 'content_type'):
            if avatar.content_type not in valid_mime_types:
                raise ValidationError(
                    'Invalid file format detected. Only PNG and JPG images are allowed.'
                )

        # Layer 3: Validate file size (5MB = 5 * 1024 * 1024 bytes)
        # Server-side enforcement in addition to form-level validation
        max_size = 5 * 1024 * 1024
        if avatar.size > max_size:
            raise ValidationError(
                f'File size too large. Maximum size is 5MB. Your file is {avatar.size / (1024 * 1024):.1f}MB.'
            )

        return avatar
