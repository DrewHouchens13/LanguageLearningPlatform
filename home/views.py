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
import logging

# Configure logger for security events
# Note: IP address logging is standard security practice for:
# - Detecting brute force attacks
# - Identifying suspicious login patterns
# - Security incident investigation and forensics
#
# Privacy Considerations:
# - IP addresses are logged for security purposes only
# - Logs should be retained according to security policy (e.g., 90 days)
# - Consider anonymizing IP addresses if storing long-term (e.g., hash last octet)
# - Comply with applicable privacy regulations (GDPR, CCPA, etc.)
# - IP addresses alone typically don't constitute PII in security logging context
#
# Log Management Best Practices:
# - Implement log rotation (see Django logging configuration in settings.py)
# - Secure log storage with restricted access (admin/security team only)
# - Regular archival of old logs to prevent storage bloat
# - Monitor logs for security incidents and suspicious patterns
logger = logging.getLogger(__name__)


def landing(request):
    """
    Render the landing page.

    This is the home page of the application, accessible to all users.
    """
    return render(request, "index.html")


def login_view(request):
    """
    Handle user login with email-based authentication.

    GET: Display login form
    POST: Authenticate user by email/password and redirect securely

    Security features:
    - Validates redirect URLs to prevent open redirect attacks
    - Uses Django's authenticate() for secure password verification
    - Generic error messages to prevent user enumeration
    """
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
            # Log failed login attempt (email not found)
            logger.warning(
                f'Failed login attempt - email not found: {email} from IP: {request.META.get("REMOTE_ADDR")}'
            )
            messages.error(request, 'Invalid email or password.')
            return render(request, 'login.html')

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # Log successful login
            logger.info(
                f'Successful login: {username} from IP: {request.META.get("REMOTE_ADDR")}'
            )
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
            # Log failed login attempt (incorrect password)
            logger.warning(
                f'Failed login attempt - incorrect password for: {username} from IP: {request.META.get("REMOTE_ADDR")}'
            )
            messages.error(request, 'Invalid email or password.')

    return render(request, 'login.html')


def signup_view(request):
    """
    Handle user registration with comprehensive validation.

    GET: Display signup form
    POST: Create new user account with validation and auto-login

    Security features:
    - Email format validation
    - Django password validators (min 8 chars, not common, not numeric only)
    - Password confirmation matching
    - Input sanitization (strip whitespace)
    - Auto-generated unique usernames from email
    - Secure error handling without information disclosure
    """
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
    """
    Render the user dashboard (protected view).

    This view requires authentication. Users must be logged in to access.
    Unauthenticated users are redirected to the login page.
    """
    return render(request, 'dashboard.html')


def progress_view(request):
    """
    Display user progress dashboard or call-to-action for guests.

    Authenticated users: Shows learning statistics including weekly and total metrics
    - Weekly: minutes studied, lessons completed, quiz accuracy
    - Total: cumulative minutes, lessons, quizzes, overall accuracy

    Unauthenticated users: Shows placeholder UI with call-to-action to sign up

    Auto-creates UserProgress record on first access for new users.
    """
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


@login_required
def account_view(request):
    """
    User account management page.

    Allows authenticated users to update:
    - Email address
    - Username
    - Password

    GET: Display account management form with current user information
    POST: Process account updates with validation

    Security features:
    - Requires authentication (@login_required)
    - Password validation for password changes
    - Email format validation
    - Username uniqueness validation
    - Current password required for email/password changes
    """
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_email':
            new_email = request.POST.get('new_email', '').strip()
            current_password = request.POST.get('current_password')

            # Verify current password
            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
                return render(request, 'account.html')

            # Validate email format
            try:
                django_validate_email(new_email)
            except ValidationError:
                messages.error(request, 'Please enter a valid email address.')
                return render(request, 'account.html')

            # Check if email already exists
            if User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
                messages.error(request, 'This email is already in use by another account.')
                return render(request, 'account.html')

            # Update email
            request.user.email = new_email
            request.user.save()
            messages.success(request, 'Email address updated successfully!')
            logger.info(f'Email updated for user: {request.user.username} from IP: {request.META.get("REMOTE_ADDR")}')

        elif action == 'update_name':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()

            # Validate first name
            if not first_name:
                messages.error(request, 'First name cannot be empty.')
                return render(request, 'account.html')

            # Update name
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.save()
            messages.success(request, 'Name updated successfully!')
            logger.info(f'Name updated for user: {request.user.username} from IP: {request.META.get("REMOTE_ADDR")}')

        elif action == 'update_username':
            new_username = request.POST.get('new_username', '').strip()

            # Validate username
            if not new_username:
                messages.error(request, 'Username cannot be empty.')
                return render(request, 'account.html')

            # Check if username already exists
            if User.objects.filter(username=new_username).exclude(id=request.user.id).exists():
                messages.error(request, 'This username is already taken.')
                return render(request, 'account.html')

            # Update username
            old_username = request.user.username
            request.user.username = new_username
            request.user.save()
            messages.success(request, f'Username updated from "{old_username}" to "{new_username}"!')
            logger.info(f'Username updated from {old_username} to {new_username} from IP: {request.META.get("REMOTE_ADDR")}')

        elif action == 'update_password':
            current_password = request.POST.get('current_password_pwd')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            # Verify current password
            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
                return render(request, 'account.html')

            # Validate passwords match
            if new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
                return render(request, 'account.html')

            # Validate password strength
            try:
                validate_password(new_password, user=request.user)
            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
                return render(request, 'account.html')

            # Update password
            request.user.set_password(new_password)
            request.user.save()

            # Re-authenticate user to maintain session
            login(request, request.user)
            messages.success(request, 'Password updated successfully!')
            logger.info(f'Password updated for user: {request.user.username} from IP: {request.META.get("REMOTE_ADDR")}')

    return render(request, 'account.html')


def forgot_password_view(request):
    """
    Handle forgot password requests.

    GET: Display forgot password form
    POST: Send password reset email if account exists

    Security features:
    - Only sends email if account exists (but doesn't confirm to prevent enumeration)
    - Generates secure token for password reset
    - Token expires after PASSWORD_RESET_TIMEOUT (20 minutes)
    - Logs password reset requests with IP addresses
    """
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.core.mail import send_mail
    from django.template.loader import render_to_string

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        try:
            user = User.objects.get(email=email)

            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # Build password reset URL
            reset_url = request.build_absolute_uri(
                f'/reset-password/{uid}/{token}/'
            )

            # Send password reset email
            subject = 'Password Reset - Language Learning Platform'
            message = render_to_string('emails/password_reset_email.txt', {
                'user': user,
                'reset_url': reset_url,
                'site_name': 'Language Learning Platform',
            })

            send_mail(
                subject,
                message,
                None,  # Use DEFAULT_FROM_EMAIL
                [user.email],
                fail_silently=False,
            )

            logger.info(f'Password reset email sent to: {email} from IP: {request.META.get("REMOTE_ADDR")}')

        except User.DoesNotExist:
            # Log failed attempt but don't inform user (prevent enumeration)
            logger.warning(f'Password reset attempted for non-existent email: {email} from IP: {request.META.get("REMOTE_ADDR")}')

        # Always show success message (don't reveal if email exists)
        messages.success(request, 'If an account with that email exists, a password reset link has been sent. Please check your email.')

    return render(request, 'forgot_password.html')


def reset_password_view(request, uidb64, token):
    """
    Handle password reset with token verification.

    Verifies the token and allows user to set a new password.

    Security features:
    - Validates token and user ID
    - Checks token expiration
    - Validates new password strength
    - Auto-logs in user after successful reset
    """
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            # Validate passwords match
            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'reset_password.html', {'valid_link': True})

            # Validate password strength
            try:
                validate_password(new_password, user=user)
            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
                return render(request, 'reset_password.html', {'valid_link': True})

            # Set new password
            user.set_password(new_password)
            user.save()

            # Log the user in
            login(request, user)

            messages.success(request, 'Your password has been reset successfully!')
            logger.info(f'Password reset completed for user: {user.username} from IP: {request.META.get("REMOTE_ADDR")}')
            return redirect('landing')

        return render(request, 'reset_password.html', {'valid_link': True})
    else:
        # Invalid or expired token
        messages.error(request, 'This password reset link is invalid or has expired.')
        return render(request, 'reset_password.html', {'valid_link': False})


def forgot_username_view(request):
    """
    Handle forgot username requests.

    GET: Display forgot username form
    POST: Send username reminder email if account exists

    Security features:
    - Only sends email if account exists (but doesn't confirm to prevent enumeration)
    - Logs username recovery requests with IP addresses
    """
    from django.core.mail import send_mail
    from django.template.loader import render_to_string

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        try:
            user = User.objects.get(email=email)

            # Send username reminder email
            subject = 'Username Reminder - Language Learning Platform'
            message = render_to_string('emails/username_reminder_email.txt', {
                'user': user,
                'site_name': 'Language Learning Platform',
            })

            send_mail(
                subject,
                message,
                None,  # Use DEFAULT_FROM_EMAIL
                [user.email],
                fail_silently=False,
            )

            logger.info(f'Username reminder sent to: {email} from IP: {request.META.get("REMOTE_ADDR")}')

        except User.DoesNotExist:
            # Log failed attempt but don't inform user (prevent enumeration)
            logger.warning(f'Username reminder attempted for non-existent email: {email} from IP: {request.META.get("REMOTE_ADDR")}')

        # Always show success message (don't reveal if email exists)
        messages.success(request, 'If an account with that email exists, a username reminder has been sent. Please check your email.')

    return render(request, 'forgot_username.html')
