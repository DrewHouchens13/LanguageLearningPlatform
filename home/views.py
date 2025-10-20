from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError


def landing(request):
    return render(request, "index.html")


def login_view(request):
    # If user is already logged in, redirect to home
    if request.user.is_authenticated:
        return redirect('landing')

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

            # Redirect to next page if specified, otherwise to landing
            next_page = request.GET.get('next', 'landing')
            return redirect(next_page)
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'login.html')


def signup_view(request):
    # If user is already logged in, redirect to home
    if request.user.is_authenticated:
        return redirect('landing')

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
            return redirect('landing')

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
    return redirect('landing')


@login_required
def dashboard(request):
    """Example of a protected view that requires login"""
    return render(request, 'dashboard.html')