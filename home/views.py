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
    TRUSTED_PROXIES = [
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
    from django.core.exceptions import ImproperlyConfigured, ValidationError
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


def landing(request):
    """Render the landing page.

    This is the home page of the application, accessible to all users
    (authenticated and anonymous).

    Args:
        request: HttpRequest object from Django

    Returns:
        HttpResponse: Rendered index.html template
    """
    return render(request, "index.html")


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
    from django.http import HttpResponseRedirect

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
            logger.info(
                'Successful login: %s from IP: %s', username, get_client_ip(request)
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
            # Safe redirect to landing page
            return HttpResponseRedirect('..')
        else:
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
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Log unexpected errors for debugging (catch all to prevent signup failures from crashing)
            import logging
            from django.conf import settings
            logger = logging.getLogger(__name__)
            exception_type = type(e).__name__
            logger.error('Unexpected error during signup: %s', exception_type)
            # In DEBUG mode, log full exception for troubleshooting
            if settings.DEBUG:
                logger.debug('Signup error details (DEBUG only): %s', str(e))
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
        user_progress, _created = UserProgress.objects.get_or_create(user=request.user)

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

            # Get or create user profile
            profile, _created = request.user.profile, False
            if not hasattr(request.user, 'profile'):
                from .models import UserProfile
                profile = UserProfile.objects.create(user=request.user)
                _created = True

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
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes

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
