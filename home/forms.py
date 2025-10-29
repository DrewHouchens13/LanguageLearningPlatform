"""
Forms for the home app, including user profile avatar upload.
"""
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
        Validate avatar upload for file type and size.

        Returns:
            File: The validated avatar file

        Raises:
            ValidationError: If file type or size is invalid
        """
        avatar = self.cleaned_data.get('avatar')

        if not avatar:
            return avatar

        # Validate file type
        valid_extensions = ['.png', '.jpg', '.jpeg']
        file_extension = avatar.name.lower().split('.')[-1]

        if f'.{file_extension}' not in valid_extensions:
            raise ValidationError(
                'Invalid file type. Only PNG and JPG images are allowed.'
            )

        # Validate file size (5MB = 5 * 1024 * 1024 bytes)
        max_size = 5 * 1024 * 1024
        if avatar.size > max_size:
            raise ValidationError(
                f'File size too large. Maximum size is 5MB. Your file is {avatar.size / (1024 * 1024):.1f}MB.'
            )

        return avatar
