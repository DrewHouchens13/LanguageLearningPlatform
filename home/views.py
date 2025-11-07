# Standard library imports
import json
import logging
from functools import wraps

# Django imports
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email
from django.db import DatabaseError, IntegrityError
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.http import require_http_methods, require_POST

# Local application imports
from .models import (
    Lesson,
    LessonAttempt,
    LessonCompletion,
    LessonQuizQuestion,
    OnboardingAnswer,
    OnboardingAttempt,
    OnboardingQuestion,
    QuizResult,
    UserProfile,
    UserProgress,
)
from .services.onboarding_service import OnboardingService

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


# =============================================================================
# ONBOARDING PROTECTION DECORATOR
# =============================================================================

def block_if_onboarding_completed(view_func):
    """
    Decorator to redirect users who have already completed onboarding.
    
    - Authenticated users with completed onboarding -> redirect to dashboard
    - Guests with completed onboarding in session -> redirect to landing
    - Others -> allow access
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check authenticated users
        if request.user.is_authenticated:
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                if user_profile.has_completed_onboarding:
                    messages.info(request, "You've already completed the placement assessment.")
                    return redirect('dashboard')
            except UserProfile.DoesNotExist:
                pass  # No profile, allow access
        
        # Check guest session
        attempt_id = request.session.get('onboarding_attempt_id')
        if attempt_id:
            try:
                attempt = OnboardingAttempt.objects.get(id=attempt_id)
                if attempt.completed_at:
                    messages.info(request, "You've already completed the assessment. Please log in to save your results.")
                    return redirect('landing')
            except OnboardingAttempt.DoesNotExist:
                pass  # Invalid attempt, allow access
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


# =============================================================================
# RATE LIMITING HELPERS
# =============================================================================

def get_client_ip(request):
    """
    Get the client's IP address, handling proxy scenarios with validation.

    When the application is behind a reverse proxy (nginx, Apache, load balancer),
    the REMOTE_ADDR will be the proxy's IP, not the client's IP. This function
    checks the X-Forwarded-For header first, which contains the real client IP.

    Args:
        request: Django request object

    Returns:
        str: Client's IP address (validated format) or 'unknown' if invalid

    Security notes:
    - X-Forwarded-For can be spoofed, so use with caution for security decisions
    - For critical security checks, consider additional validation
    - Only the first IP in X-Forwarded-For chain is used (client IP)
    - IP addresses are validated to ensure proper format
    - In production, X-Forwarded-For is only trusted from known proxies (Render, DevEDU)
    """
    import ipaddress
    from django.conf import settings

    # Get REMOTE_ADDR first (this is always the direct connection IP)
    remote_addr = request.META.get('REMOTE_ADDR', 'unknown')

    # Trusted proxy IP ranges (adjust for your deployment)
    # Render.com uses various IPs, DevEDU varies, localhost for development
    _ = [
        '127.0.0.1',  # Localhost (development)
        '::1',  # Localhost IPv6
        # Add your production proxy IPs here when deploying
        # e.g., '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16' for private networks
    ]

    # Check if request is behind a trusted proxy
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    # Only trust X-Forwarded-For based on TRUST_X_FORWARDED_FOR setting
    should_trust_xff = False
    if x_forwarded_for:
        trust_mode = getattr(settings, 'TRUST_X_FORWARDED_FOR', 'always')

        if trust_mode == 'always':
            # Always trust X-Forwarded-For (for Render, Heroku, etc.)
            should_trust_xff = True
        elif trust_mode == 'debug':
            # Only trust in DEBUG mode (for DevEDU development)
            should_trust_xff = settings.DEBUG
        elif trust_mode == 'never':
            # Never trust X-Forwarded-For (most secure, but won't work behind proxies)
            should_trust_xff = False
        else:
            # Invalid setting - raise exception in production, warn in debug
            error_msg = (
                f'Invalid TRUST_X_FORWARDED_FOR setting: "{trust_mode}". '
                f'Must be one of: "always", "debug", or "never". '
                f'See config/settings.py for configuration details.'
            )
            if settings.DEBUG:
                # Development: log warning and default to DEBUG mode to allow debugging
                logger.warning('%s Defaulting to debug mode.', error_msg)
                should_trust_xff = True
            else:
                # Production: raise exception to prevent running with unknown configuration
                from django.core.exceptions import ImproperlyConfigured
                logger.error(error_msg)
                raise ImproperlyConfigured(error_msg)

    if should_trust_xff and x_forwarded_for:
        # X-Forwarded-For can contain multiple IPs: "client, proxy1, proxy2"
        # Take the first one (the client IP)
        ip_address = x_forwarded_for.split(',')[0].strip()

        # Validate IP address format to prevent injection attacks
        try:
            ipaddress.ip_address(ip_address)
            return ip_address
        except ValueError:
            # Invalid IP format in X-Forwarded-For, fall back to REMOTE_ADDR
            logger.warning('Invalid IP in X-Forwarded-For header: %s, using REMOTE_ADDR instead', ip_address)

    # Direct connection (no proxy) or untrusted/invalid X-Forwarded-For
    ip_address = remote_addr

    # Validate REMOTE_ADDR as well
    if ip_address != 'unknown':
        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            logger.warning('Invalid REMOTE_ADDR: %s', ip_address)
            ip_address = 'unknown'

    return ip_address


def check_rate_limit(request, action, limit=5, period=300):
    """
    Simple rate limiting using Django's cache framework.

    Args:
        request: Django request object
        action: String identifier for the action (e.g., 'password_reset')
        limit: Maximum number of attempts allowed (default: 5)
        period: Time period in seconds (default: 300 = 5 minutes)

    Returns:
        tuple: (is_allowed, attempts_remaining, retry_after)
            - is_allowed: Boolean indicating if request should be allowed
            - attempts_remaining: Number of attempts left before rate limit
            - retry_after: Seconds until rate limit resets (if rate limited)

    Rate limiting strategy:
    - Uses IP address as the rate limit key
    - Tracks number of requests per IP per action
    - Implements sliding window rate limiting
    - Prevents abuse of password reset and username reminder endpoints

    Privacy note: IP addresses are temporarily cached for rate limiting only
    and automatically expire after the rate limit period.
    """
    from django.core.cache import cache

    # Get client IP address (handles proxies)
    ip_address = get_client_ip(request)

    # Create cache key combining action and IP
    cache_key = f'ratelimit_{action}_{ip_address}'

    # Get current attempt count
    attempts = cache.get(cache_key, 0)

    if attempts >= limit:
        # Rate limit exceeded
        # Try to get TTL if cache backend supports it, otherwise use period
        try:
            ttl = cache.ttl(cache_key)
            retry_after = ttl if ttl and ttl > 0 else period
        except AttributeError:
            # Cache backend doesn't support TTL (e.g., LocMemCache), use period
            retry_after = period
        logger.warning('Rate limit exceeded for %s from IP: %s', action, ip_address)
        return False, 0, retry_after

    # Increment attempt counter
    cache.set(cache_key, attempts + 1, period)

    return True, limit - attempts - 1, 0


def send_template_email(request, template_name, context, subject, recipient_email, log_prefix, max_retries=3):
    """Send an email using a template with comprehensive error handling and retry logic.

    This helper function reduces code duplication for email sending operations
    like password reset and username reminders. Implements exponential backoff
    retry mechanism for improved reliability.

    Args:
        request: Django request object (for IP logging)
        template_name: Path to email template (e.g., 'emails/password_reset_email.txt')
        context: Dictionary of template context variables
        subject: Email subject line
        recipient_email: Email address to send to
        log_prefix: Prefix for log messages (e.g., 'Password reset email')
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        bool: True if email sent successfully, False otherwise

    Raises:
        ImproperlyConfigured: If DEFAULT_FROM_EMAIL is not set in Django settings

    Example:
        success = send_template_email(
            request,
            'emails/password_reset_email.txt',
            {'user': user, 'reset_url': url},
            'Password Reset - Language Learning Platform',
            user.email,
            'Password reset email'
        )
    """
    from django.core.mail import send_mail, BadHeaderError
    from django.template.loader import render_to_string
    from django.core.exceptions import ImproperlyConfigured
    from django.core.validators import validate_email
    from django.conf import settings
    from smtplib import SMTPException
    import time

    # Validate email configuration before attempting to send
    if not hasattr(settings, 'DEFAULT_FROM_EMAIL') or not settings.DEFAULT_FROM_EMAIL:
        error_msg = (
            'DEFAULT_FROM_EMAIL is not configured in Django settings. '
            'Email sending requires a valid from address.'
        )
        logger.error('%s Attempted to send: %s', error_msg, log_prefix)
        raise ImproperlyConfigured(error_msg)

    # Validate recipient email format before attempting to send
    try:
        validate_email(recipient_email)
    except ValidationError:
        logger.error('Invalid recipient email format: %s for %s from IP: %s',
                     recipient_email, log_prefix, get_client_ip(request))
        return False

    # Render email template
    message = render_to_string(template_name, context)

    # Retry mechanism with exponential backoff
    for attempt in range(max_retries):
        try:
            send_mail(
                subject,
                message,
                None,  # Use DEFAULT_FROM_EMAIL
                [recipient_email],
                fail_silently=False,
            )
            if attempt > 0:
                logger.info('%s sent to: %s on retry %s from IP: %s',
                           log_prefix, recipient_email, attempt, get_client_ip(request))
            else:
                logger.info('%s sent to: %s from IP: %s',
                           log_prefix, recipient_email, get_client_ip(request))
            return True
        except (SMTPException, BadHeaderError) as e:
            # Log attempt failure (sanitize exception to avoid leaking SMTP credentials)
            exception_type = type(e).__name__
            logger.warning('Email send attempt %s/%s failed for %s to %s: %s',
                          attempt + 1, max_retries, log_prefix.lower(), recipient_email, exception_type)

            # If this was the last attempt, log error and return False
            if attempt == max_retries - 1:
                logger.error('Failed to send %s to %s after %s attempts from IP: %s',
                            log_prefix.lower(), recipient_email, max_retries, get_client_ip(request))
                # In DEBUG mode, log full exception for troubleshooting
                if settings.DEBUG:
                    logger.debug('SMTP Error details (DEBUG only): %s', str(e))
                return False

            # Exponential backoff: wait 2^attempt seconds (1s, 2s, 4s, ...)
            wait_time = 2 ** attempt
            logger.info('Retrying email send in %s seconds...', wait_time)
            time.sleep(wait_time)

    # If loop completes without success, return False
    return False


def landing(request):
    """Render the landing page.

    This is the home page of the application for guests only.
    Logged-in users are automatically redirected to their dashboard.

    Args:
        request: HttpRequest object from Django

    Returns:
        HttpResponse: Rendered index.html template (guests) or redirect to dashboard (authenticated)
    """
    # Redirect logged-in users to dashboard (their "Home")
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Guest users see the landing page
    context = {
        'has_completed_onboarding': False
    }
    return render(request, "index.html", context)


def login_view(request):
    """Handle user login with username or email-based authentication.

    GET: Display login form
    POST: Authenticate user by username/email and password, redirect securely

    Args:
        request: HttpRequest object from Django

    Returns:
        HttpResponse: Rendered login.html template or redirect to landing page

    Security features:
        - Rate limiting: 5 attempts per 5 minutes per IP to prevent brute force attacks
        - Input validation: Empty field checks, length limits (max 254 chars)
        - Character whitelist: Only alphanumeric and safe email characters (@._+-)
        - Validates redirect URLs to prevent open redirect attacks
        - Uses Django's authenticate() for secure password verification
        - Generic error messages to prevent user enumeration
        - Logs all login attempts with IP addresses for security monitoring
        - Django ORM parameterized queries prevent SQL injection

    Authentication flow:
        - Accepts either username or email for login
        - Validates and sanitizes input before processing
        - First attempts to find user by username
        - If not found, attempts to find user by email
        - Authenticates with Django's built-in authentication system
    """
    # If user is already logged in, redirect to home
    if request.user.is_authenticated:
        return HttpResponseRedirect('..')

    if request.method == 'POST':
        # Rate limiting: Prevent brute force attacks (5 attempts per 5 minutes per IP)
        is_allowed, _attempts_remaining, retry_after = check_rate_limit(
            request,
            action='login',
            limit=5,
            period=300
        )

        if not is_allowed:
            logger.warning(
                'Login rate limit exceeded from IP: %s, retry after %s seconds',
                get_client_ip(request), retry_after
            )
            messages.error(
                request,
                f'Too many login attempts. Please try again in {retry_after // 60} minute(s).'
            )
            return render(request, 'login.html')

        username_or_email = request.POST.get('username_or_email', '').strip()
        password = request.POST.get('password', '')

        # Input validation: Check for empty fields
        if not username_or_email or not password:
            messages.error(request, 'Please provide both username/email and password.')
            return render(request, 'login.html')

        # Input validation: Check length to prevent excessively long inputs
        if len(username_or_email) > 254:  # Max email length per RFC 5321
            logger.warning(
                'Login attempt with excessively long username/email from IP: %s',
                get_client_ip(request)
            )
            messages.error(request, 'Invalid username/email or password.')
            return render(request, 'login.html')

        # Input validation: Allow only safe characters (alphanumeric, @, ., _, -, +)
        # This prevents potential injection attacks while allowing valid usernames and emails
        import re
        if not re.match(r'^[a-zA-Z0-9@._+\-]+$', username_or_email):
            logger.warning(
                'Login attempt with invalid characters in username/email from IP: %s',
                get_client_ip(request)
            )
            messages.error(request, 'Invalid username/email or password.')
            return render(request, 'login.html')

        # Find user by username or email
        user_obj = None
        try:
            # First, try to find by username
            user_obj = User.objects.get(username=username_or_email)
        except User.DoesNotExist:
            # If not found by username, try email
            try:
                user_obj = User.objects.get(email=username_or_email)
            except User.DoesNotExist:
                # Log failed login attempt (username/email not found)
                logger.warning(
                    'Failed login attempt - user not found: %s from IP: %s',
                    username_or_email, get_client_ip(request)
                )
                messages.error(request, 'Invalid username/email or password.')
                return render(request, 'login.html')

        # Authenticate user with their username
        username = user_obj.username
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # Log successful login
            logger.info('Successful login: %s from IP: %s', username, get_client_ip(request))
            
            # Check if user completed onboarding as a guest (only redirect if it's unlinked)
            onboarding_attempt_id = request.session.get('onboarding_attempt_id')
            if onboarding_attempt_id:
                try:
                    # Get the attempt
                    attempt = OnboardingAttempt.objects.get(id=onboarding_attempt_id)
                    
                    # Only process if this attempt is NOT yet linked to a user
                    # (This prevents redirect on subsequent logins)
                    if not attempt.user:
                        # Link attempt to user
                        attempt.user = user
                        attempt.save()
                        
                        # Create/update user profile with onboarding data
                        user_profile, _ = UserProfile.objects.get_or_create(user=user)
                        
                        # Only update if user hasn't completed onboarding or this is newer
                        if not user_profile.has_completed_onboarding or not user_profile.onboarding_completed_at or attempt.completed_at > user_profile.onboarding_completed_at:
                            user_profile.proficiency_level = attempt.calculated_level
                            user_profile.has_completed_onboarding = True
                            user_profile.onboarding_completed_at = attempt.completed_at or timezone.now()
                            user_profile.target_language = attempt.language
                            user_profile.save()
                            
                            # Populate stats from guest onboarding
                            QuizResult.objects.create(
                                user=user,
                                quiz_id=f'onboarding_{attempt.language}',
                                quiz_title=f'{attempt.language} Placement Assessment',
                                score=attempt.total_score,
                                total_questions=attempt.total_possible
                            )
                            
                            # Calculate total time from all answers
                            total_time_minutes = sum(
                                answer.time_taken_seconds for answer in attempt.answers.all()
                            ) // 60  # Convert seconds to minutes
                            
                            # Update UserProgress
                            user_progress, _ = UserProgress.objects.get_or_create(user=user)
                            user_progress.total_minutes_studied += total_time_minutes
                            user_progress.total_quizzes_taken += 1
                            user_progress.overall_quiz_accuracy = user_progress.calculate_quiz_accuracy()
                            user_progress.save()
                        
                        logger.info('Linked onboarding attempt %s to user %s', attempt.id, user.username)
                        
                        # Clear session AFTER getting the ID
                        request.session.pop('onboarding_attempt_id', None)
                        
                        # Redirect to results page with attempt ID in URL
                        messages.success(request, f'Welcome back, {user.first_name or user.username}! Your assessment results have been saved.')
                        results_url = f"{reverse('onboarding_results')}?attempt={attempt.id}"
                        return redirect(results_url)

                    # Attempt already linked - clear stale session data and continue normal flow
                    request.session.pop('onboarding_attempt_id', None)
                    logger.info('Cleared stale onboarding session for user %s', user.username)
                except OnboardingAttempt.DoesNotExist:
                    # Clear invalid session data
                    request.session.pop('onboarding_attempt_id', None)
                    logger.warning('Onboarding attempt %s not found, cleared session', onboarding_attempt_id)
                except (ValueError, TypeError, AttributeError) as e:
                    # Handle data/attribute errors gracefully
                    logger.error('Error linking onboarding attempt to user: %s', str(e))
            
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')

            # Redirect to next page if specified and safe, otherwise go to dashboard (home for logged-in users)
            next_page = request.GET.get('next', '')
            if next_page and url_has_allowed_host_and_scheme(
                url=next_page,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return HttpResponseRedirect(next_page)

            # Redirect to dashboard (home for authenticated users)
            return redirect('dashboard')

        # Log failed login attempt (incorrect password)
        logger.warning(
            'Failed login attempt - incorrect password for: %s from IP: %s',
            username, get_client_ip(request)
        )
        messages.error(request, 'Invalid username/email or password.')

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

        # Check if email already exists before attempting creation
        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'login.html')

        try:
            # Create new user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            logger.info('New user created: %s (%s) from IP: %s', user.username, email, get_client_ip(request))

        except IntegrityError as e:
            # This shouldn't happen since we checked, but handle it anyway
            logger.error('IntegrityError during user creation: %s from IP: %s', str(e), get_client_ip(request))
            messages.error(request, 'An error occurred while creating your account. Please try again.')
            return render(request, 'login.html')
        except (ValueError, TypeError, ValidationError, DatabaseError) as e:
            # Log unexpected validation/data/database errors for debugging (don't expose details to user)
            from django.conf import settings
            exception_type = type(e).__name__
            logger.error('Unexpected error during user creation: %s from IP: %s', exception_type, get_client_ip(request))
            if settings.DEBUG:
                logger.debug('User creation error details (DEBUG only): %s', str(e))
            messages.error(request, 'An error occurred while creating your account. Please try again.')
            return render(request, 'login.html')

        # User created successfully, now log them in
        login(request, user)
        
        # Check if user completed onboarding as a guest
        onboarding_attempt_id = request.session.get('onboarding_attempt_id')
        if onboarding_attempt_id:
            try:
                # Get the attempt
                attempt = OnboardingAttempt.objects.get(id=onboarding_attempt_id)
                
                # Link attempt to new user
                attempt.user = user
                attempt.save()
                
                # Create user profile with onboarding data
                user_profile, _ = UserProfile.objects.get_or_create(user=user)
                user_profile.proficiency_level = attempt.calculated_level
                user_profile.has_completed_onboarding = True
                user_profile.onboarding_completed_at = attempt.completed_at or timezone.now()
                user_profile.target_language = attempt.language
                user_profile.save()
                
                # Populate stats from guest onboarding
                QuizResult.objects.create(
                    user=user,
                    quiz_id=f'onboarding_{attempt.language}',
                    quiz_title=f'{attempt.language} Placement Assessment',
                    score=attempt.total_score,
                    total_questions=attempt.total_possible
                )
                
                # Calculate total time from all answers
                total_time_minutes = sum(
                    answer.time_taken_seconds for answer in attempt.answers.all()
                ) // 60  # Convert seconds to minutes
                
                # Update UserProgress
                user_progress, _ = UserProgress.objects.get_or_create(user=user)
                user_progress.total_minutes_studied += total_time_minutes
                user_progress.total_quizzes_taken += 1
                user_progress.overall_quiz_accuracy = user_progress.calculate_quiz_accuracy()
                user_progress.save()
                
                logger.info('Linked onboarding attempt %s to new user %s', attempt.id, user.username)
                
                # Clear session AFTER getting the ID
                request.session.pop('onboarding_attempt_id', None)
                
                # Redirect to results page with attempt ID in URL
                messages.success(request, f'Welcome to Language Learning Platform, {first_name}! Your assessment results have been saved.')
                results_url = f"{reverse('onboarding_results')}?attempt={attempt.id}"
                return redirect(results_url)
            except OnboardingAttempt.DoesNotExist:
                logger.warning('Onboarding attempt %s not found for new user %s', onboarding_attempt_id, user.username)
                # Continue with normal signup flow
            except (ValueError, TypeError, AttributeError) as e:
                # Handle data/attribute errors gracefully
                logger.error('Error linking onboarding attempt to new user %s: %s', user.username, str(e))
                # Continue with normal signup flow - user is created, just onboarding link failed
        
        messages.success(request, f'Welcome to Language Learning Platform, {first_name}!')
        # Redirect to dashboard (home for authenticated users)
        return redirect('dashboard')

    return render(request, 'login.html')


@require_POST
def logout_view(request):
    """
    Logout view that only accepts POST requests for CSRF protection.
    Use a form with method="POST" to log out users securely.
    """
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    # Use absolute redirect to avoid double prefix issue in admin
    # Build absolute URL using request scheme and host
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
    # Check if user has completed onboarding
    has_completed_onboarding = False
    user_profile = None
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        has_completed_onboarding = user_profile.has_completed_onboarding
    except UserProfile.DoesNotExist:
        has_completed_onboarding = False
    
    # Clean up stale onboarding session data
    # (Prevents redirect issues on return visits with persistent sessions)
    if 'onboarding_attempt_id' in request.session:
        try:
            attempt_id = request.session['onboarding_attempt_id']
            attempt = OnboardingAttempt.objects.get(id=attempt_id)
            
            # If attempt is already linked to this user, clear the session
            if attempt.user == request.user:
                request.session.pop('onboarding_attempt_id', None)
                logger.info('Cleared stale onboarding session for user %s on dashboard', request.user.username)
        except OnboardingAttempt.DoesNotExist:
            # Invalid attempt ID, clear it
            logger.warning('Invalid onboarding attempt ID in session for user %s, clearing', request.user.username)
            request.session.pop('onboarding_attempt_id', None)
        except (KeyError, AttributeError, ValueError) as e:
            # Any other error, clear it to be safe
            logger.error('Error checking onboarding session on dashboard: %s', str(e))
            if 'onboarding_attempt_id' in request.session:
                request.session.pop('onboarding_attempt_id', None)
    
    context = {
        'has_completed_onboarding': has_completed_onboarding,
        'user_profile': user_profile
    }
    return render(request, 'dashboard.html', context)


def progress_view(request):
    """
    Display user progress dashboard or call-to-action for guests.

    Authenticated users: Shows learning statistics including weekly and total metrics
    - Weekly: minutes studied, lessons completed, quiz accuracy
    - Total: cumulative minutes, lessons, quizzes, overall accuracy
    - Onboarding: proficiency level and assessment results

    Unauthenticated users: Shows placeholder UI with call-to-action to sign up

    Auto-creates UserProgress record on first access for new users.
    """
    if request.user.is_authenticated:
        # Get or create user progress record
        user_progress, _ = UserProgress.objects.get_or_create(user=request.user)

        # Get weekly stats
        weekly_stats = user_progress.get_weekly_stats()

        # Get onboarding/profile information
        user_profile = None
        latest_attempt = None
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            # Get most recent completed onboarding attempt
            latest_attempt = OnboardingAttempt.objects.filter(
                user=request.user,
                completed_at__isnull=False
            ).first()
        except UserProfile.DoesNotExist:
            pass

        # Prepare context for authenticated users
        context = {
            'weekly_minutes': weekly_stats['weekly_minutes'],
            'weekly_lessons': weekly_stats['weekly_lessons'],
            'weekly_accuracy': weekly_stats['weekly_accuracy'],
            'total_minutes': user_progress.total_minutes_studied,
            'total_lessons': user_progress.total_lessons_completed,
            'total_quizzes': user_progress.total_quizzes_taken,
            'overall_accuracy': user_progress.overall_quiz_accuracy,
            'user_profile': user_profile,
            'latest_onboarding_attempt': latest_attempt,
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
            'user_profile': None,
            'latest_onboarding_attempt': None,
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
            logger.info('Email updated for user: %s from IP: %s',
                       request.user.username, get_client_ip(request))

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
            logger.info('Name updated for user: %s from IP: %s',
                       request.user.username, get_client_ip(request))

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
            logger.info('Username updated from %s to %s from IP: %s',
                       old_username, new_username, get_client_ip(request))

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

            # Update session auth hash to keep user logged in
            # This prevents invalidating the current session after password change
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)

            messages.success(request, 'Password updated successfully!')
            logger.info('Password updated for user: %s from IP: %s',
                       request.user.username, get_client_ip(request))

        elif action == 'update_avatar':
            from .forms import AvatarUploadForm

            try:
                # Get or create user profile
                try:
                    profile = request.user.profile
                except UserProfile.DoesNotExist:
                    profile = UserProfile.objects.create(user=request.user)

                form = AvatarUploadForm(request.POST, request.FILES, instance=profile)

                if form.is_valid():
                    form.save()
                    messages.success(request, 'Avatar updated successfully!')
                    logger.info('Avatar updated for user: %s from IP: %s',
                               request.user.username, get_client_ip(request))
                else:
                    for error_list in form.errors.values():
                        for error in error_list:
                            messages.error(request, error)
            except (IOError, OSError, ValidationError, ValueError) as e:
                # Log the full exception for debugging
                logger.error('Avatar upload failed for user %s: %s',
                           request.user.username, str(e), exc_info=True)
                messages.error(request, 'Avatar upload failed. Please try again.')

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
    - Error handling for email sending failures
    - Rate limiting: 5 requests per 5 minutes per IP address
    """
    if request.method == 'POST':
        # Check rate limit (5 requests per 5 minutes)
        is_allowed, _attempts_remaining, retry_after = check_rate_limit(
            request, 'password_reset', limit=5, period=300
        )

        if not is_allowed:
            messages.error(
                request,
                f'Too many password reset attempts. Please try again in {retry_after // 60} minutes.'
            )
            return render(request, 'forgot_password.html')

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

            # Render simulated email (for college project - no real SMTP)
            from django.template.loader import render_to_string
            email_content = render_to_string('emails/password_reset_email.txt', {
                'user': user,
                'reset_url': reset_url,
                'site_name': 'Language Learning Platform',
            })

            # Show simulated email in styled box
            return render(request, 'forgot_password.html', {
                'simulated_email': {
                    'to': user.email,
                    'subject': 'Password Reset - Language Learning Platform',
                    'content': email_content,
                }
            })

        except User.DoesNotExist:
            # Log failed attempt but don't inform user (prevent enumeration)
            logger.warning('Password reset attempted for non-existent email: %s from IP: %s',
                          email, get_client_ip(request))

        # Always show success message (don't reveal if email exists or sending failed)
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
            logger.info('Password reset completed for user: %s from IP: %s',
                       user.username, get_client_ip(request))
            return redirect('landing')

        return render(request, 'reset_password.html', {'valid_link': True})
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
    - Error handling for email sending failures
    - Rate limiting: 5 requests per 5 minutes per IP address
    """
    if request.method == 'POST':
        # Check rate limit (5 requests per 5 minutes)
        is_allowed, _attempts_remaining, retry_after = check_rate_limit(
            request, 'username_reminder', limit=5, period=300
        )

        if not is_allowed:
            messages.error(
                request,
                f'Too many username reminder attempts. Please try again in {retry_after // 60} minutes.'
            )
            return render(request, 'forgot_username.html')

        email = request.POST.get('email', '').strip()

        try:
            user = User.objects.get(email=email)

            # Build login URL
            login_url = request.build_absolute_uri('/login/')

            # Render simulated email (for college project - no real SMTP)
            from django.template.loader import render_to_string
            email_content = render_to_string('emails/username_reminder_email.txt', {
                'user': user,
                'site_name': 'Language Learning Platform',
                'login_url': login_url,
            })

            # Show simulated email in styled box
            return render(request, 'forgot_username.html', {
                'simulated_email': {
                    'to': user.email,
                    'subject': 'Username Reminder - Language Learning Platform',
                    'content': email_content,
                }
            })

        except User.DoesNotExist:
            # Log failed attempt but don't inform user (prevent enumeration)
            logger.warning('Username reminder attempted for non-existent email: %s from IP: %s',
                          email, get_client_ip(request))

        # Always show success message (don't reveal if email exists or sending failed)
        messages.success(request, 'If an account with that email exists, a username reminder has been sent. Please check your email.')

    return render(request, 'forgot_username.html')


# =============================================================================
# ONBOARDING ASSESSMENT VIEWS
# =============================================================================

@block_if_onboarding_completed
def onboarding_welcome(request):
    """
    Landing page for onboarding assessment.
    
    Explains the assessment, shows start button.
    Available to all users (guests and authenticated).
    
    Users who have already completed onboarding are redirected to dashboard.
    """
    user_profile = None
    if request.user.is_authenticated:
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    context = {
        'user_profile': user_profile
    }
    return render(request, 'onboarding/welcome.html', context)


@block_if_onboarding_completed
def onboarding_quiz(request):
    """
    Display the onboarding quiz with 10 questions.
    
    GET: Load questions, create attempt, render quiz
    
    For guests: Generates session key for tracking
    For authenticated: Links attempt to user
    
    Creates OnboardingAttempt with started_at timestamp.
    """
    # Get questions for language (Spanish default)
    language = request.GET.get('language', 'Spanish')
    service = OnboardingService()
    questions = service.get_questions_for_language(language)
    
    if questions.count() != 10:
        messages.error(request, f'Assessment not available for {language}. Please contact support.')
        return redirect('onboarding_welcome')
    
    # Ensure session exists for guests
    if not request.session.session_key:
        request.session.create()
    
    # Create OnboardingAttempt
    attempt = OnboardingAttempt.objects.create(
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key,
        language=language
    )
    
    # Store attempt_id in session for later retrieval
    request.session['onboarding_attempt_id'] = attempt.id
    
    context = {
        'questions': questions,
        'attempt_id': attempt.id,
        'language': language,
        'is_guest': not request.user.is_authenticated
    }
    
    return render(request, 'onboarding/quiz.html', context)


def submit_onboarding(request):
    """
    Process onboarding quiz submission (AJAX endpoint).
    
    POST: Accept answers, calculate level, update profile
    
    Expects JSON:
    {
        "attempt_id": 123,
        "answers": [
            {"question_id": 1, "answer": "B", "time_taken": 15},
            ...
        ]
    }
    
    Returns JSON:
    {
        "success": true,
        "level": "A2",
        "score": 12,
        "total": 19,
        "percentage": 63.2,
        "redirect_url": "/onboarding/results/?attempt=123"
    }
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        attempt_id = data.get('attempt_id')
        answers = data.get('answers', [])
        
        # Validate input
        if not attempt_id or not answers:
            return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)
        
        if len(answers) != 10:
            return JsonResponse({'success': False, 'error': 'Must answer all 10 questions'}, status=400)
        
        # Get attempt
        try:
            attempt = OnboardingAttempt.objects.get(id=attempt_id)
        except OnboardingAttempt.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid attempt ID'}, status=404)
        
        # Check if already completed
        if attempt.completed_at:
            return JsonResponse({'success': False, 'error': 'Assessment already submitted'}, status=400)
        
        # Process answers and calculate score
        answers_data = []
        total_score = 0
        total_possible = 0
        
        for answer_item in answers:
            question_id = answer_item.get('question_id')
            user_answer = answer_item.get('answer', '').strip().upper()
            time_taken = answer_item.get('time_taken', 0)
            
            try:
                question = OnboardingQuestion.objects.get(id=question_id)
            except OnboardingQuestion.DoesNotExist:
                return JsonResponse({'success': False, 'error': f'Invalid question ID: {question_id}'}, status=400)
            
            # Check if answer is correct
            is_correct = user_answer == question.correct_answer.upper()
            
            # Save answer
            OnboardingAnswer.objects.create(
                attempt=attempt,
                question=question,
                user_answer=user_answer,
                is_correct=is_correct,
                time_taken_seconds=time_taken
            )
            
            # Track for level calculation
            answers_data.append({
                'difficulty_level': question.difficulty_level,
                'is_correct': is_correct,
                'difficulty_points': question.difficulty_points,
                'question_number': question.question_number
            })
            
            # Calculate score
            total_possible += question.difficulty_points
            if is_correct:
                total_score += question.difficulty_points
        
        # Calculate proficiency level
        service = OnboardingService()
        calculated_level = service.calculate_proficiency_level(answers_data)
        
        # Update attempt
        attempt.calculated_level = calculated_level
        attempt.total_score = total_score
        attempt.total_possible = total_possible
        attempt.completed_at = timezone.now()
        attempt.save()
        
        # For authenticated users, update profile AND stats
        if request.user.is_authenticated:
            user_profile, _created = UserProfile.objects.get_or_create(user=request.user)
            user_profile.proficiency_level = calculated_level
            user_profile.has_completed_onboarding = True
            user_profile.onboarding_completed_at = timezone.now()
            user_profile.save()
            
            # Create QuizResult for stats tracking
            QuizResult.objects.create(
                user=request.user,
                quiz_id=f'onboarding_{attempt.language}',
                quiz_title=f'{attempt.language} Placement Assessment',
                score=total_score,
                total_questions=total_possible
            )
            
            # Calculate total time from all answers
            total_time_minutes = sum(
                answer_item.get('time_taken', 0) for answer_item in answers
            ) // 60  # Convert seconds to minutes
            
            # Update UserProgress
            user_progress, _ = UserProgress.objects.get_or_create(user=request.user)
            user_progress.total_minutes_studied += total_time_minutes
            user_progress.total_quizzes_taken += 1
            user_progress.overall_quiz_accuracy = user_progress.calculate_quiz_accuracy()
            user_progress.save()
            
            logger.info('Onboarding completed for user %s: %s (%s/%s)', request.user.username, calculated_level, total_score, total_possible)
        else:
            # For guests, store attempt_id in session
            request.session['onboarding_attempt_id'] = attempt.id
            logger.info('Onboarding completed for guest session %s: %s (%s/%s)', attempt.session_key, calculated_level, total_score, total_possible)
        
        # Calculate percentage
        percentage = round((total_score / total_possible * 100), 1) if total_possible > 0 else 0
        
        return JsonResponse({
            'success': True,
            'level': calculated_level,
            'score': total_score,
            'total': total_possible,
            'percentage': percentage,
            'redirect_url': f'/onboarding/results/?attempt={attempt.id}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except (KeyError, ValueError, AttributeError, TypeError) as e:
        logger.error('Error processing onboarding submission: %s', str(e))
        return JsonResponse({'success': False, 'error': 'Internal server error'}, status=500)


def onboarding_results(request):
    """
    Display onboarding assessment results.
    
    Shows:
    - Calculated proficiency level with badge
    - Score breakdown (total and by level)
    - Explanation of level
    - Next steps (dashboard for authenticated, signup for guests)
    
    GET params:
    - attempt: OnboardingAttempt ID
    
    Falls back to session storage for guests.
    """
    # Get attempt ID from query param or session
    attempt_id = request.GET.get('attempt')
    if not attempt_id:
        attempt_id = request.session.get('onboarding_attempt_id')
    
    # For logged-in users, if no attempt ID or attempt already linked, redirect to home
    if request.user.is_authenticated and not attempt_id:
        messages.info(request, 'Assessment already completed. Check your dashboard for your level.')
        return redirect('dashboard')
    
    if not attempt_id:
        messages.error(request, 'No assessment results found. Please take the assessment first.')
        return redirect('onboarding_welcome')
    
    try:
        attempt = OnboardingAttempt.objects.get(id=attempt_id)
    except OnboardingAttempt.DoesNotExist:
        messages.error(request, 'Assessment results not found.')
        return redirect('onboarding_welcome')
    
    # Check if attempt is completed
    if not attempt.completed_at:
        messages.error(request, 'Assessment not yet completed.')
        return redirect('onboarding_quiz')
    
    # Get answer breakdown by level
    answers = attempt.answers.all()
    breakdown = {
        'A1': {'correct': 0, 'total': 0},
        'A2': {'correct': 0, 'total': 0},
        'B1': {'correct': 0, 'total': 0}
    }
    
    for answer in answers:
        level = answer.question.difficulty_level
        breakdown[level]['total'] += 1
        if answer.is_correct:
            breakdown[level]['correct'] += 1
    
    # Calculate percentages for each level
    for level, data in breakdown.items():
        if data['total'] > 0:
            data['percentage'] = round(
                (data['correct'] / data['total']) * 100, 1
            )
        else:
            breakdown[level]['percentage'] = 0
    
    # Level descriptions
    level_descriptions = {
        'A1': 'Beginner - You can understand and use familiar everyday expressions and very basic phrases.',
        'A2': 'Elementary - You can understand sentences and frequently used expressions related to everyday topics.',
        'B1': 'Intermediate - You can understand the main points of clear standard input on familiar matters and produce simple connected text.'
    }
    
    # Get user profile if authenticated
    user_profile = None
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            pass
    
    context = {
        'attempt': attempt,
        'breakdown': breakdown,
        'level_description': level_descriptions.get(attempt.calculated_level, ''),
        'percentage': attempt.score_percentage,
        'user_profile': user_profile,
        'is_guest': not request.user.is_authenticated
    }
    
    return render(request, 'onboarding/results.html', context)

# =============================================================================
# LESSON VIEWS
# =============================================================================

def lessons_list(request):
    """Display list of all available lessons."""
    lessons = Lesson.objects.filter(is_published=True).order_by('order', 'id')
    return render(request, 'lessons_list.html', {'lessons': lessons})


def lesson_detail(request, lesson_id):
    """Display lesson detail with flashcards."""
    lesson = get_object_or_404(Lesson, id=lesson_id, is_published=True)
    cards = lesson.cards.all()
    context = {'lesson': lesson, 'cards': cards}
    return render(request, 'lessons/lesson_detail.html', context)


def lesson_quiz(request, lesson_id):
    """Display quiz for a specific lesson."""
    lesson = get_object_or_404(Lesson, id=lesson_id, is_published=True)
    questions = lesson.quiz_questions.all()
    qlist = []
    for q in questions:
        qlist.append({
            'id': q.id,
            'order': q.order,
            'question': q.question,
            'options': q.options,
        })
    # Use dynamic template based on lesson slug
    template_name = f'lessons/{lesson.slug}/quiz.html'
    return render(request, template_name, {'lesson': lesson, 'questions': qlist})


@require_http_methods(["POST"])
def submit_lesson_quiz(request, lesson_id):
    """Process lesson quiz submission."""
    lesson = get_object_or_404(Lesson, id=lesson_id, is_published=True)

    # Accept JSON body or regular POST
    try:
        if request.content_type == 'application/json':
            payload = json.loads(request.body.decode('utf-8'))
        else:
            payload = request.POST.dict()
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("Invalid JSON payload in quiz submission for lesson %s", lesson_id)
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)

    answers = payload.get('answers')

    # Handle answers as JSON string (for backwards compatibility with form-encoded submissions)
    if answers and isinstance(answers, str):
        try:
            answers = json.loads(answers)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse answers JSON string for lesson %s", lesson_id)
            return JsonResponse({'error': 'Invalid answers format - must be valid JSON'}, status=400)

    if not answers or not isinstance(answers, list):
        return JsonResponse({'error': 'No answers provided or invalid format'}, status=400)

    # Fetch all quiz questions for this lesson in one query (performance optimization)
    # Create a dictionary for O(1) lookup by question ID
    questions = {q.id: q for q in LessonQuizQuestion.objects.filter(lesson=lesson)}

    # Evaluate answers
    score = 0
    total = 0
    for a in answers:
        # Skip non-dict elements (security: handle malformed payloads gracefully)
        if not isinstance(a, dict):
            continue

        qid = a.get('question_id') or a.get('id')
        sel = a.get('selected_index') if 'selected_index' in a else a.get('selected')

        # Skip if missing required fields
        if qid is None or sel is None:
            continue

        # Lookup question from pre-fetched dictionary (O(1) instead of database query)
        q = questions.get(qid)
        if not q:
            # Question ID not found or doesn't belong to this lesson
            continue

        total += 1
        if int(sel) == int(q.correct_index):
            score += 1

    attempt = LessonAttempt.objects.create(
        lesson=lesson,
        user=request.user if request.user.is_authenticated else None,
        score=score,
        total=total
    )

    # Track stats for authenticated users
    if request.user.is_authenticated:
        # Create QuizResult for stats tracking
        QuizResult.objects.create(
            user=request.user,
            quiz_id=f'lesson_{lesson.id}',
            quiz_title=lesson.title,
            score=score,
            total_questions=total
        )
        
        # Create LessonCompletion record
        LessonCompletion.objects.create(
            user=request.user,
            lesson_id=str(lesson.id),
            lesson_title=lesson.title,
            duration_minutes=5  # Estimated time per lesson quiz
        )

        # Award XP for lesson completion (Sprint 3 - Issue #17)
        base_xp = 50  # Base XP per lesson
        bonus_xp = 10 if total > 0 and score == total else 0  # Bonus for perfect score
        total_xp_awarded = base_xp + bonus_xp

        # Safely get or create profile (defensive programming)
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            # Profile should exist (auto-created by signal), but create if missing
            profile = UserProfile.objects.create(user=request.user)
            logger.warning('UserProfile was missing for user %s, created new profile', request.user.username)

        # Award XP with error handling
        try:
            xp_result = profile.award_xp(total_xp_awarded)
            logger.info(
                'XP awarded: %s earned %s XP (Level %s -> %s)',
                request.user.username,
                xp_result["xp_awarded"],
                xp_result["old_level"],
                xp_result["new_level"] or xp_result["old_level"]
            )
        except (ValueError, TypeError) as e:
            # XP awarding failed, log but don't block lesson completion
            logger.error('Failed to award XP for user %s: %s', request.user.username, str(e))
            xp_result = None

        # Update UserProgress
        user_progress, _ = UserProgress.objects.get_or_create(user=request.user)
        user_progress.total_quizzes_taken += 1
        user_progress.total_lessons_completed += 1
        user_progress.overall_quiz_accuracy = user_progress.calculate_quiz_accuracy()
        user_progress.save()

        logger.info('Lesson quiz completed: %s - %s: %s/%s', request.user.username, lesson.title, score, total)

    # If request from JS expect JSON
    if request.content_type == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response_data = {
            'success': True,
            'score': score,
            'total': total,
            'attempt_id': attempt.id,
            'redirect_url': reverse('lesson_results', args=[lesson.id, attempt.id])
        }

        # Add XP info for authenticated users (Sprint 3 - Issue #17)
        if request.user.is_authenticated and xp_result is not None:
            response_data['xp'] = {
                'awarded': xp_result['xp_awarded'],
                'total': xp_result['total_xp'],
                'leveled_up': xp_result['leveled_up'],
                'new_level': xp_result['new_level'],
                'old_level': xp_result['old_level']
            }

        return JsonResponse(response_data)
    return redirect('lesson_results', lesson_id=lesson.id, attempt_id=attempt.id)


def lesson_results(request, lesson_id, attempt_id):
    """Display results for a completed lesson quiz."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    attempt = get_object_or_404(LessonAttempt, id=attempt_id, lesson=lesson)
    next_lesson = lesson.next_lesson
    context = {'lesson': lesson, 'attempt': attempt, 'next_lesson': next_lesson}
    # Use dynamic template based on lesson slug
    template_name = f'lessons/{lesson.slug}/results.html'
    return render(request, template_name, context)
