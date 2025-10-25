from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email
from django.contrib import messages
from django.db import IntegrityError
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods


def landing(request):
    return render(request, "index.html")


def login_view(request):
    from django.http import HttpResponseRedirect

    # If user is already logged in, redirect to home
    if request.user.is_authenticated:
        return HttpResponseRedirect('..')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Find user by email
        try:
            user = User.objects.get(email=email)
            username = user.username
        except User.DoesNotExist:
            messages.error(request, 'Invalid email or password.')
            return render(request, 'login.html')

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')

            # Redirect to next page if specified and safe, otherwise go to landing
            next_page = request.GET.get('next', '')
            if next_page and url_has_allowed_host_and_scheme(
                url=next_page,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return HttpResponseRedirect(next_page)
            else:
                # Safe redirect to landing page
                return HttpResponseRedirect('..')
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'login.html')


def signup_view(request):
    from django.http import HttpResponseRedirect

    # If user is already logged in, redirect to home
    if request.user.is_authenticated:
        return HttpResponseRedirect('..')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm-password')

        # Validate email format
        try:
            django_validate_email(email)
        except ValidationError:
            messages.error(request, 'Please enter a valid email address.')
            return render(request, 'login.html')

        # Validate passwords match
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'login.html')

        # Validate password strength using Django's validators
        try:
            # Create a temporary user object for validation
            temp_user = User(username=email.split('@')[0], email=email, first_name=name.split()[0] if name else '')
            validate_password(password, user=temp_user)
        except ValidationError as e:
            # Display all password validation errors
            for error in e.messages:
                messages.error(request, error)
            return render(request, 'login.html')

        # Split name into first and last name
        name_parts = name.strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Create username from email (before @ symbol)
        username = email.split('@')[0]

        # Check if username already exists, if so, add numbers
        original_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{original_username}{counter}"
            counter += 1

        try:
            # Create new user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Log the user in
            login(request, user)
            messages.success(request, f'Welcome to Language Learning Platform, {first_name}!')
            return HttpResponseRedirect('..')

        except IntegrityError as e:
            # Check if it's email duplicate or username duplicate
            if 'email' in str(e):
                messages.error(request, 'An account with this email already exists.')
            else:
                messages.error(request, 'An error occurred while creating your account. Please try again.')
            return render(request, 'login.html')
        except ValidationError as e:
            # Handle any validation errors
            for error in e.messages:
                messages.error(request, error)
            return render(request, 'login.html')
        except Exception as e:
            # Log unexpected errors for debugging (don't expose details to user)
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Unexpected error during signup: {str(e)}')
            messages.error(request, 'An error occurred while creating your account. Please try again.')
            return render(request, 'login.html')

    return render(request, 'login.html')


@require_http_methods(["GET", "POST"])
def logout_view(request):
    """
    Logout view that accepts both GET and POST for compatibility.
    GET is allowed for navigation links, but POST is recommended for security.
    """
    if request.method == 'POST' or request.method == 'GET':
        logout(request)
        messages.success(request, 'You have been successfully logged out.')
        # Use absolute redirect to avoid double prefix issue in admin
        # Build absolute URL using request scheme and host
        from django.urls import reverse
        from django.http import HttpResponseRedirect
        landing_url = reverse('landing')
        absolute_url = request.build_absolute_uri(landing_url)
        return HttpResponseRedirect(absolute_url)


@login_required
def dashboard(request):
    """Example of a protected view that requires login"""
    return render(request, 'dashboard.html')


def progress_view(request):
    """Progress dashboard - shows stats for logged-in users, CTA for guests"""
    if request.user.is_authenticated:
        # Get or create user progress record
        from .models import UserProgress
        user_progress, created = UserProgress.objects.get_or_create(user=request.user)
        
        # Get weekly stats
        weekly_stats = user_progress.get_weekly_stats()
        
        # Prepare context for authenticated users
        context = {
            'weekly_minutes': weekly_stats['weekly_minutes'],
            'weekly_lessons': weekly_stats['weekly_lessons'],
            'weekly_accuracy': weekly_stats['weekly_accuracy'],
            'total_minutes': user_progress.total_minutes_studied,
            'total_lessons': user_progress.total_lessons_completed,
            'total_quizzes': user_progress.total_quizzes_taken,
            'overall_accuracy': user_progress.overall_quiz_accuracy,
        }
    else:
        # Context for guest users (all None/empty)
        context = {
            'weekly_minutes': None,
            'weekly_lessons': None,
            'weekly_accuracy': None,
            'total_minutes': None,
            'total_lessons': None,
            'total_quizzes': None,
            'overall_accuracy': None,
        }
    
    return render(request, 'progress.html', context)
