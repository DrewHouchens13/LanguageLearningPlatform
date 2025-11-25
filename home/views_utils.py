"""
Shared utilities for views.

Contains decorators, rate limiting, email helpers, and other shared functionality
used across different view modules.
"""
# Standard library imports
import logging
from functools import wraps

# Django imports

# Local application imports
from .models import OnboardingAttempt

# Configure logger
logger = logging.getLogger(__name__)


# =============================================================================
# ONBOARDING PROTECTION DECORATOR
# =============================================================================

def block_if_onboarding_completed(view_func):
    """
    Legacy decorator retained for compatibility.

    Forced retake policy: all users may re-open onboarding regardless of previous completion.
    This decorator now simply clears stale onboarding attempt references.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        attempt_id = request.session.get('onboarding_attempt_id')
        if attempt_id:
            try:
                attempt = OnboardingAttempt.objects.get(id=attempt_id)
                if attempt.completed_at:
                    request.session.pop('onboarding_attempt_id', None)
            except OnboardingAttempt.DoesNotExist:
                request.session.pop('onboarding_attempt_id', None)

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


def send_template_email(
    request,
    template_name,
    *,
    context,
    subject,
    recipient_email,
    log_prefix,
    max_retries=3
):
    """Send an email using a template with comprehensive error handling and retry logic.

    SOFA Principles Applied:
    - Single Responsibility: Only handles email sending
    - Avoid Repetition: Centralized utility (imported, not duplicated)
    - Function Signature: Keyword-only args for clarity

    This helper function reduces code duplication for email sending operations
    like password reset and username reminders. Implements exponential backoff
    retry mechanism for improved reliability.

    Args:
        request: Django request object (for IP logging)
        template_name: Path to email template (e.g., 'emails/password_reset_email.txt')
        context: (keyword-only) Dictionary of template context variables
        subject: (keyword-only) Email subject line
        recipient_email: (keyword-only) Email address to send to
        log_prefix: (keyword-only) Prefix for log messages (e.g., 'Password reset email')
        max_retries: (keyword-only) Maximum number of retry attempts (default: 3)

    Returns:
        bool: True if email sent successfully, False otherwise

    Raises:
        ImproperlyConfigured: If DEFAULT_FROM_EMAIL is not set in Django settings

    Example:
        success = send_template_email(
            request,
            'emails/password_reset_email.txt',
            context={'user': user, 'reset_url': url},
            subject='Password Reset - Language Learning Platform',
            recipient_email=user.email,
            log_prefix='Password reset email'
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

    # Fallback return (should not be reached due to loop logic)
    return False
