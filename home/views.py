from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError


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

            # Redirect to next page if specified, otherwise go up one level from /login/
            next_page = request.GET.get('next')
            if not next_page:
                # Simple relative redirect - go up from /login/ to parent directory
                # Works correctly through proxy: /proxy/8000/login/ -> /proxy/8000/
                next_page = '..'
            return HttpResponseRedirect(next_page)
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'login.html')


def signup_view(request):
    from django.http import HttpResponseRedirect

    # If user is already logged in, redirect to home
    if request.user.is_authenticated:
        return HttpResponseRedirect('..')

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm-password')

        # Validate passwords match
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'login.html')

        # Validate password length
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
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

        except IntegrityError:
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'login.html')
        except Exception as e:
            messages.error(request, 'An error occurred while creating your account. Please try again.')
            return render(request, 'login.html')

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    # Use named URL redirect - FORCE_SCRIPT_NAME will handle proxy prefix
    return redirect('landing')


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