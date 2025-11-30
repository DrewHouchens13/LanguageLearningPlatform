"""
View functions for the Language Learning Platform.

Handles all HTTP request processing including:
- Authentication (login, signup, logout, password recovery)
- Dashboard and landing pages
- User profile and account management
- Onboarding assessment system
- Lesson viewing and quiz submission
- Daily Quest system
- Progress tracking and XP management

All views follow Django best practices with proper decorators,
authentication checks, and error handling.
"""
# Standard library imports
import json
import logging
import random
import re
import time
from collections import defaultdict
from functools import wraps
from smtplib import SMTPException

from django.conf import settings
# Django imports
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.mail import BadHeaderError, send_mail
from django.core.validators import validate_email as django_validate_email
from django.db import DatabaseError, IntegrityError
from django.db.models import Q, Sum
from django.http import (Http404, HttpResponse, HttpResponseRedirect,
                         JsonResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string, select_template
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import (url_has_allowed_host_and_scheme,
                               urlsafe_base64_decode, urlsafe_base64_encode)
from django.views.decorators.http import require_http_methods, require_POST

# Local application imports
from .language_registry import (DEFAULT_LANGUAGE, get_language_metadata,
                                get_supported_languages,
                                normalize_language_name)
from .models import (Lesson, LessonAttempt, LessonCompletion,
                     LessonQuizQuestion, OnboardingAnswer, OnboardingAttempt,
                     OnboardingQuestion, QuizResult, UserDailyQuestAttempt,
                     UserLanguageProfile, UserProfile, UserProgress)
from .services.chatbot_service import ChatbotService
from .services.daily_quest_service import DailyQuestService
from .services.help_service import HelpService
from .services.onboarding_service import OnboardingService
from .services.adaptive_test_service import AdaptiveTestService
from .services.tts_service import TTSService

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


# Import shared utilities (SOFA: Avoid Repetition - centralized in views_utils.py)
from .views_utils import (block_if_onboarding_completed, check_rate_limit,
                          get_client_ip, send_template_email)


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


def _validate_login_input(request, username_or_email, password):
    """Validate login input (SOFA extracted)."""
    # Check for empty fields
    if not username_or_email or not password:
        messages.error(request, 'Please provide both username/email and password.')
        return False

    # Check length to prevent excessively long inputs
    if len(username_or_email) > 254:  # Max email length per RFC 5321
        logger.warning(
            'Login attempt with excessively long username/email from IP: %s',
            get_client_ip(request)
        )
        messages.error(request, 'Invalid username/email or password.')
        return False

    # Allow only safe characters (alphanumeric, @, ., _, -, +)
    # Note: re already imported at module level (no shadowing - SOFA principle)
    if not re.match(r'^[a-zA-Z0-9@._+\-]+$', username_or_email):
        logger.warning(
            'Login attempt with invalid characters in username/email from IP: %s',
            get_client_ip(request)
        )
        messages.error(request, 'Invalid username/email or password.')
        return False

    return True


def _find_user_by_username_or_email(request, username_or_email):
    """Find user by username or email (SOFA extracted)."""
    try:
        # First, try to find by username
        return User.objects.get(username=username_or_email)
    except User.DoesNotExist:
        # If not found by username, try email
        try:
            return User.objects.get(email=username_or_email)
        except User.DoesNotExist:
            # Log failed login attempt (username/email not found)
            logger.warning(
                'Failed login attempt - user not found: %s from IP: %s',
                username_or_email, get_client_ip(request)
            )
            messages.error(request, 'Invalid username/email or password.')
            return None


def _get_or_create_language_profile(user, language):
    """Return the per-language profile for a user (auto-creates if missing)."""
    normalized_language = normalize_language_name(language)
    profile, _ = UserLanguageProfile.objects.get_or_create(
        user=user,
        language=normalized_language
    )
    return profile


def _upsert_language_onboarding(user, language, proficiency_level, completed_at=None):
    """Update onboarding metadata for a specific language."""
    language_profile = _get_or_create_language_profile(user, language)
    # Convert CEFR level (A1, A2, B1) to integer (1, 2, 3) if needed
    if isinstance(proficiency_level, str):
        cefr_to_level = {'A1': 1, 'A2': 2, 'B1': 3}
        language_profile.proficiency_level = cefr_to_level.get(proficiency_level, 1)
    else:
        language_profile.proficiency_level = proficiency_level
    language_profile.has_completed_onboarding = True
    language_profile.onboarding_completed_at = completed_at or timezone.now()
    language_profile.save(update_fields=[
        'proficiency_level',
        'has_completed_onboarding',
        'onboarding_completed_at',
        'updated_at',
    ])
    return language_profile


def _increment_language_study_stats(user, language, minutes=0, lessons=0, quizzes=0):
    """Increment per-language study counters."""
    if minutes <= 0 and lessons <= 0 and quizzes <= 0:
        return None

    language_profile = _get_or_create_language_profile(user, language)
    changed_fields = []

    if minutes > 0:
        language_profile.total_minutes_studied += minutes
        changed_fields.append('total_minutes_studied')

    if lessons > 0:
        language_profile.total_lessons_completed += lessons
        changed_fields.append('total_lessons_completed')

    if quizzes > 0:
        language_profile.total_quizzes_taken += quizzes
        changed_fields.append('total_quizzes_taken')

    if changed_fields:
        changed_fields.append('updated_at')
        language_profile.save(update_fields=changed_fields)

    return language_profile


def _award_language_xp(user, language, amount):
    """Award XP for a specific language profile."""
    if amount <= 0:
        return None
    language_profile = _get_or_create_language_profile(user, language)
    try:
        return language_profile.award_xp(amount)
    except (ValueError, TypeError):
        logger.error('Failed to award %s XP for %s (%s)', amount, user.username, language)
        return None


def _link_onboarding_attempt_to_user(request, user):
    """Link guest onboarding attempt to newly authenticated user (SOFA extracted)."""
    onboarding_attempt_id = request.session.get('onboarding_attempt_id')
    if not onboarding_attempt_id:
        return None

    try:
        # Get the attempt
        attempt = OnboardingAttempt.objects.get(id=onboarding_attempt_id)

        # Only process if this attempt is NOT yet linked to a user
        if not attempt.user:
            # Link attempt to user
            attempt.user = user
            attempt.save()

            # Create/update user profile with onboarding data
            user_profile, _ = UserProfile.objects.get_or_create(user=user)

            # Only update if user hasn't completed onboarding or this is newer
            if (not user_profile.has_completed_onboarding or
                not user_profile.onboarding_completed_at or
                attempt.completed_at > user_profile.onboarding_completed_at):

                normalized_language = normalize_language_name(attempt.language)
                
                # Convert CEFR level (A1, A2, B1) to integer (1, 2, 3) if needed
                if isinstance(attempt.calculated_level, str):
                    cefr_to_level = {'A1': 1, 'A2': 2, 'B1': 3}
                    user_profile.proficiency_level = cefr_to_level.get(attempt.calculated_level, 1)
                else:
                    user_profile.proficiency_level = attempt.calculated_level
                
                user_profile.has_completed_onboarding = True
                user_profile.onboarding_completed_at = attempt.completed_at or timezone.now()
                user_profile.target_language = normalized_language
                user_profile.save()
                _upsert_language_onboarding(
                    user,
                    normalized_language,
                    attempt.calculated_level,
                    attempt.completed_at
                )

                # Populate stats from guest onboarding
                QuizResult.objects.create(
                    user=user,
                    quiz_id=f'onboarding_{attempt.language}',
                    quiz_title=f'{attempt.language} Placement Assessment',
                    language=normalized_language,
                    score=attempt.total_score,
                    total_questions=attempt.total_possible
                )

                # Calculate total time from all answers
                total_time_minutes = sum(
                    answer.time_taken_seconds for answer in attempt.answers.all()
                ) // 60

                # Update UserProgress
                user_progress, _ = UserProgress.objects.get_or_create(user=user)
                user_progress.total_minutes_studied += total_time_minutes
                user_progress.total_quizzes_taken += 1
                user_progress.overall_quiz_accuracy = user_progress.calculate_quiz_accuracy()
                user_progress.save()
                _increment_language_study_stats(
                    user,
                    normalized_language,
                    minutes=total_time_minutes,
                    quizzes=1
                )

            logger.info('Linked onboarding attempt %s to user %s', attempt.id, user.username)

            # Clear session AFTER getting the ID
            request.session.pop('onboarding_attempt_id', None)

            # Return attempt to trigger redirect to results
            return attempt

        # Attempt already linked - clear stale session data
        request.session.pop('onboarding_attempt_id', None)
        logger.info('Cleared stale onboarding session for user %s', user.username)
        return None

    except OnboardingAttempt.DoesNotExist:
        # Clear invalid session data
        request.session.pop('onboarding_attempt_id', None)
        logger.warning('Onboarding attempt %s not found, cleared session', onboarding_attempt_id)
        return None
    except (ValueError, TypeError, AttributeError) as e:
        # Handle data/attribute errors gracefully
        logger.error('Error linking onboarding attempt to user: %s', str(e))
        return None


def _get_post_login_redirect(request, user):
    """
    Determine redirect destination after successful login.

    Priority: onboarding results > next parameter > dashboard

    SOFA: Function Extraction - Reduces R0911 warning by consolidating redirect logic.

    Args:
        request: Django request object
        user: Authenticated user object

    Returns:
        HttpResponse: Redirect to appropriate destination
    """
    # Check for onboarding link first
    linked_attempt = _link_onboarding_attempt_to_user(request, user)
    if linked_attempt:
        results_url = f"{reverse('onboarding_results')}?attempt={linked_attempt.id}"
        return redirect(results_url)

    # Check for next page parameter
    next_page = request.GET.get('next', '')
    if next_page and url_has_allowed_host_and_scheme(
        url=next_page,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        return HttpResponseRedirect(next_page)

    # Default redirect to dashboard
    return redirect('dashboard')


def _process_login_post(request):
    """
    Process POST login request.

    SOFA: Function Extraction - Reduces R0911 warning by consolidating POST logic.
    Returns redirect response on success, None on failure (to re-render form).

    Args:
        request: Django request object (must be POST)

    Returns:
        HttpResponse: Redirect on success, None on failure
    """
    # Rate limiting: Prevent brute force attacks
    is_allowed, _attempts_remaining, retry_after = check_rate_limit(
        request, action='login', limit=5, period=300
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
        return None

    username_or_email = request.POST.get('username_or_email', '').strip()
    password = request.POST.get('password', '')

    # Validate input
    if not _validate_login_input(request, username_or_email, password):
        return None

    # Find user
    user_obj = _find_user_by_username_or_email(request, username_or_email)
    if not user_obj:
        return None

    # Authenticate user
    user = authenticate(request, username=user_obj.username, password=password)

    if user is None:
        # Log failed login attempt (incorrect password)
        # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
        logger.warning(
            'Failed login attempt - incorrect password for: %s from IP: %s',
            user_obj.username, get_client_ip(request)
        )
        messages.error(request, 'Invalid username/email or password.')
        return None

    # Successful login
    login(request, user)
    logger.info('Successful login: %s from IP: %s', user.username, get_client_ip(request))

    return _get_post_login_redirect(request, user)


def login_view(request):
    """Handle user login (SOFA refactored)."""
    # If user is already logged in, redirect to home
    if request.user.is_authenticated:
        return HttpResponseRedirect('..')

    # Process POST login if submitted
    if request.method == 'POST':
        # Rate limiting: Prevent brute force attacks
        is_allowed, _attempts_remaining, retry_after = check_rate_limit(
            request, action='login', limit=5, period=300
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

        # Validate input (SOFA - extracted function)
        if not _validate_login_input(request, username_or_email, password):
            return render(request, 'login.html')

        # Find user (SOFA - extracted function)
        user_obj = _find_user_by_username_or_email(request, username_or_email)
        if not user_obj:
            return render(request, 'login.html')

        # Authenticate user
        user = authenticate(request, username=user_obj.username, password=password)

        if user is not None:
            login(request, user)
            logger.info('Successful login: %s from IP: %s', user.username, get_client_ip(request))

            # Link onboarding attempt if exists (SOFA - extracted function)
            linked_attempt = _link_onboarding_attempt_to_user(request, user)
            if linked_attempt:
                results_url = f"{reverse('onboarding_results')}?attempt={linked_attempt.id}"
                return redirect(results_url)

            # Redirect to next page if specified and safe
            next_page = request.GET.get('next', '')
            if next_page and url_has_allowed_host_and_scheme(
                url=next_page,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return HttpResponseRedirect(next_page)

            return redirect('dashboard')

        # Log failed authentication attempt (audit trail - username/IP only)
        logger.warning(
            'Failed authentication attempt - user: %s, IP: %s',
            user_obj.username, get_client_ip(request)
        )
        messages.error(request, 'Invalid username/email or password.')

    return render(request, 'login.html')


def _validate_signup_input(request, name, email, password, confirm_password):
    """
    Validate signup form input.

    SOFA: Function Extraction - Reduces R0914/R0915 warnings by isolating validation logic.

    Args:
        request: Django request object (for messages)
        name: User's full name
        email: User's email address
        password: User's password
        confirm_password: Password confirmation

    Returns:
        tuple: (first_name, last_name) on success, (None, None) on failure
    """
    # Validate email format
    try:
        django_validate_email(email)
    except ValidationError:
        messages.error(request, 'Please enter a valid email address.')
        return None, None

    # Validate passwords match
    if password != confirm_password:
        messages.error(request, 'Passwords do not match.')
        return None, None

    # Validate password strength using Django's validators
    try:
        # Create a temporary user object for validation
        temp_user = User(username=email.split('@')[0], email=email, first_name=name.split()[0] if name else '')
        validate_password(password, user=temp_user)
    except ValidationError as e:
        # Display all password validation errors
        for error in e.messages:
            messages.error(request, error)
        return None, None

    # Split name into first and last name
    name_parts = name.strip().split(' ', 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ''

    return first_name, last_name


def _generate_unique_username(email):
    """
    Generate a unique username from email address.

    SOFA: Function Extraction - Single Responsibility principle.

    Args:
        email: User's email address

    Returns:
        str: Unique username
    """
    username = email.split('@')[0]
    original_username = username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{original_username}{counter}"
        counter += 1
    return username


def _link_guest_onboarding_to_user(request, user, first_name):
    """
    Link guest onboarding attempt to newly created user account.

    SOFA: Function Extraction - Reduces R0914/R0915 warnings by isolating onboarding logic.

    Args:
        request: Django request object
        user: Newly created User object
        first_name: User's first name (for welcome message)

    Returns:
        HttpResponse: Redirect to onboarding results, or None to continue normal flow
    """
    onboarding_attempt_id = request.session.get('onboarding_attempt_id')
    if not onboarding_attempt_id:
        return None

    try:
        # Get the attempt
        attempt = OnboardingAttempt.objects.get(id=onboarding_attempt_id)

        # Link attempt to new user
        attempt.user = user
        attempt.save()

        # Create user profile with onboarding data
        user_profile, _ = UserProfile.objects.get_or_create(user=user)
        normalized_language = normalize_language_name(attempt.language)
        
        # Convert CEFR level (A1, A2, B1) to integer (1, 2, 3) if needed
        if isinstance(attempt.calculated_level, str):
            cefr_to_level = {'A1': 1, 'A2': 2, 'B1': 3}
            user_profile.proficiency_level = cefr_to_level.get(attempt.calculated_level, 1)
        else:
            user_profile.proficiency_level = attempt.calculated_level
        
        user_profile.has_completed_onboarding = True
        user_profile.onboarding_completed_at = attempt.completed_at or timezone.now()
        user_profile.target_language = normalized_language
        user_profile.save()

        _upsert_language_onboarding(
            user,
            normalized_language,
            attempt.calculated_level,
            attempt.completed_at
        )

        # Populate stats from guest onboarding
        QuizResult.objects.create(
            user=user,
            quiz_id=f'onboarding_{attempt.language}',
            quiz_title=f'{attempt.language} Placement Assessment',
            language=normalized_language,
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

        _increment_language_study_stats(
            user,
            normalized_language,
            minutes=total_time_minutes,
            quizzes=1
        )

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

    return None


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

    if request.method != 'POST':
        return render(request, 'login.html')

    # Get form inputs
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password')
    confirm_password = request.POST.get('confirm-password')

    # Validate input (SOFA: Extracted helper)
    first_name, last_name = _validate_signup_input(request, name, email, password, confirm_password)
    if not first_name:
        return render(request, 'login.html')

    # Generate unique username (SOFA: Extracted helper)
    username = _generate_unique_username(email)

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
        exception_type = type(e).__name__
        logger.error('Unexpected error during user creation: %s from IP: %s', exception_type, get_client_ip(request))
        if settings.DEBUG:
            logger.debug('User creation error details (DEBUG only): %s', str(e))
        messages.error(request, 'An error occurred while creating your account. Please try again.')
        return render(request, 'login.html')

    # User created successfully, now log them in
    login(request, user)

    # Check if user completed onboarding as a guest (SOFA: Extracted helper)
    onboarding_redirect = _link_guest_onboarding_to_user(request, user, first_name)
    if onboarding_redirect:
        return onboarding_redirect

    messages.success(request, f'Welcome to Language Learning Platform, {first_name}!')
    return redirect('dashboard')


@require_POST
def logout_view(request):
    """
    Logout view that only accepts POST requests for CSRF protection.
    Use a form with method="POST" to log out users securely.
    """
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    # Use safe redirect to landing page (fixes open redirect CWE-601)
    return redirect('landing')


def _cleanup_onboarding_session(request):
    """
    Clean up stale onboarding session data.

    SOFA: Function Extraction - Reduces R0912/R0915 warnings by isolating session logic.

    Args:
        request: Django request object with session
    """
    if 'onboarding_attempt_id' not in request.session:
        return

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

    # Clean up stale onboarding session data (SOFA: Extracted helper)
    _cleanup_onboarding_session(request)

    # Get today's daily quests status (Sprint 3 - Issue #18)
    daily_challenge = None
    try:
        daily_challenge = DailyQuestService.get_today_challenge(request.user)
        if daily_challenge:
            logger.info(
                'Daily challenge loaded for dashboard: language=%s completed=%s',
                daily_challenge['quest'].language,
                daily_challenge['is_completed']
            )
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error('Failed to load daily challenge for dashboard: %s', str(e), exc_info=True)

    # Get XP and streak data
    user_progress = None
    current_streak = 0
    xp_to_next = 0
    xp_progress_percent = 0

    if user_profile:
        xp_to_next = user_profile.get_xp_to_next_level()
        xp_progress_percent = user_profile.get_progress_to_next_level()

    try:
        user_progress = UserProgress.objects.get(user=request.user)
        current_streak = user_progress.current_streak
    except UserProgress.DoesNotExist:
        pass

    # Get language statistics (SOFA: Reusing extracted helper)
    language_stats, pending_languages = _get_language_statistics(request.user)

    preferred_language = DEFAULT_LANGUAGE
    if user_profile and user_profile.target_language:
        preferred_language = normalize_language_name(user_profile.target_language)
    elif language_stats:
        preferred_language = language_stats[0]['name']

    # Get current language profile
    current_language_profile = UserLanguageProfile.objects.filter(
        user=request.user,
        language=preferred_language
    ).first()

    overall_xp_row = None
    if user_profile:
        overall_xp_row = {
            'label': 'Overall',
            'flag': '⭐',
            'level': user_profile.current_level,
            'xp': user_profile.total_xp,
            'xp_to_next': xp_to_next,
            'progress_percent': xp_progress_percent,
        }

    # SOFA: Inline metadata call to reduce local variable count (R0914)
    context = {
        'has_completed_onboarding': has_completed_onboarding,
        'user_profile': user_profile,
        'daily_challenge': daily_challenge,
        'user_progress': user_progress,
        'current_streak': current_streak,
        'xp_to_next_level': xp_to_next,
        'xp_progress_percent': xp_progress_percent,
        'language_stats': language_stats,
        'pending_languages': pending_languages,
        'current_language_profile': current_language_profile,
        'current_language_metadata': get_language_metadata(preferred_language),
        'current_language_name': preferred_language,
        'overall_xp_row': overall_xp_row,
    }
    return render(request, 'dashboard.html', context)


def _get_language_statistics(user):
    """
    Get language statistics for progress view.

    SOFA: Function Extraction - Reduces R0914 warning by isolating language stats logic.

    Args:
        user: Django User object

    Returns:
        tuple: (language_stats, pending_languages)
            - language_stats: List of dicts with active language statistics
            - pending_languages: List of dicts with languages not yet started
    """
    language_profiles = UserLanguageProfile.objects.filter(user=user)
    language_profile_map = {lp.language: lp for lp in language_profiles}
    supported_languages = get_supported_languages(include_flags=True)

    language_stats = []
    pending_languages = []

    for entry in supported_languages:
        profile = language_profile_map.get(entry['name'])
        if profile and (
            profile.has_completed_onboarding or
            profile.total_minutes_studied > 0 or
            profile.total_lessons_completed > 0 or
            profile.total_xp > 0
        ):
            language_stats.append({
                'name': entry['name'],
                'native_name': entry['native_name'],
                'flag': entry['flag'],
                'slug': entry['slug'],
                'minutes': profile.total_minutes_studied,
                'lessons': profile.total_lessons_completed,
                'xp': profile.total_xp,
                'quizzes': profile.total_quizzes_taken,
                'proficiency': profile.get_proficiency_level_display() if profile.proficiency_level else 'Not assessed',
                'has_completed_onboarding': profile.has_completed_onboarding,
                'level': profile.current_level,
            })
        else:
            pending_languages.append(entry)

    return language_stats, pending_languages


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

        # Get XP and leveling data (Sprint 3 - Issue #17)
        if user_profile:
            xp_to_next = user_profile.get_xp_to_next_level()
            progress_percent = user_profile.get_progress_to_next_level()
        else:
            xp_to_next = 0
            progress_percent = 0

        # Get language statistics (SOFA: Extracted helper)
        language_stats, pending_languages = _get_language_statistics(request.user)

        weekly_challenge = DailyQuestService.get_weekly_stats(request.user)
        lifetime_challenge = DailyQuestService.get_lifetime_stats(request.user)

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
            # XP and leveling data
            'xp_to_next_level': xp_to_next,
            'xp_progress_percent': progress_percent,
            'language_stats': language_stats,
            'pending_languages': pending_languages,
            # Daily challenge stats
            'weekly_challenges_completed': weekly_challenge['challenges_completed'],
            'weekly_challenge_xp': weekly_challenge['xp_earned'],
            'weekly_challenge_accuracy': weekly_challenge['accuracy'],
            'total_challenges_completed': lifetime_challenge['challenges_completed'],
            'total_challenge_xp': lifetime_challenge['xp_earned'],
            'lifetime_challenge_accuracy': lifetime_challenge['accuracy'],
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
            'language_stats': [],
            'pending_languages': [],
            'weekly_challenges_completed': 0,
            'weekly_challenge_xp': 0,
            'weekly_challenge_accuracy': 0,
            'total_challenges_completed': 0,
            'total_challenge_xp': 0,
            'lifetime_challenge_accuracy': 0,
        }

    return render(request, 'progress.html', context)


def _handle_update_email(request):
    """Handle email update action (SOFA extracted)."""
    new_email = request.POST.get('new_email', '').strip()
    current_password = request.POST.get('current_password')

    # Verify current password
    if not request.user.check_password(current_password):
        messages.error(request, 'Current password is incorrect.')
        return False

    # Validate email format
    try:
        django_validate_email(new_email)
    except ValidationError:
        messages.error(request, 'Please enter a valid email address.')
        return False

    # Check if email already exists
    if User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
        messages.error(request, 'This email is already in use by another account.')
        return False

    # Update email
    request.user.email = new_email
    request.user.save()
    messages.success(request, 'Email address updated successfully!')
    logger.info('Email updated for user: %s from IP: %s',
               request.user.username, get_client_ip(request))
    return True


def _handle_update_name(request):
    """Handle name update action (SOFA extracted)."""
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()

    # Validate first name
    if not first_name:
        messages.error(request, 'First name cannot be empty.')
        return False

    # Update name
    request.user.first_name = first_name
    request.user.last_name = last_name
    request.user.save()
    messages.success(request, 'Name updated successfully!')
    logger.info('Name updated for user: %s from IP: %s',
               request.user.username, get_client_ip(request))
    return True


def _handle_update_username(request):
    """Handle username update action (SOFA extracted)."""
    new_username = request.POST.get('new_username', '').strip()

    # Validate username
    if not new_username:
        messages.error(request, 'Username cannot be empty.')
        return False

    # Check if username already exists
    if User.objects.filter(username=new_username).exclude(id=request.user.id).exists():
        messages.error(request, 'This username is already taken.')
        return False

    # Update username
    old_username = request.user.username
    request.user.username = new_username
    request.user.save()
    messages.success(request, f'Username updated from "{old_username}" to "{new_username}"!')
    logger.info('Username updated from %s to %s from IP: %s',
               old_username, new_username, get_client_ip(request))
    return True


def _handle_update_password(request):
    """Handle password update action (SOFA extracted)."""
    current_password = request.POST.get('current_password_pwd')
    new_password = request.POST.get('new_password')
    confirm_password = request.POST.get('confirm_password')

    # Verify current password
    if not request.user.check_password(current_password):
        messages.error(request, 'Current password is incorrect.')
        return False

    # Validate passwords match
    if new_password != confirm_password:
        messages.error(request, 'New passwords do not match.')
        return False

    # Validate password strength
    try:
        validate_password(new_password, user=request.user)
    except ValidationError as e:
        for error in e.messages:
            messages.error(request, error)
        return False

    # Update password
    request.user.set_password(new_password)
    request.user.save()

    # Update session auth hash to keep user logged in
    from django.contrib.auth import update_session_auth_hash
    update_session_auth_hash(request, request.user)

    messages.success(request, 'Password updated successfully!')
    logger.info(
        'Account security change - user: %s, IP: %s, action: password_update',
        request.user.username, get_client_ip(request))
    return True


def _handle_update_avatar(request):
    """Handle avatar update action (SOFA extracted)."""
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
            return True

        for error_list in form.errors.values():
            for error in error_list:
                messages.error(request, error)
        return False
    except (IOError, OSError, ValidationError, ValueError) as e:
        logger.error('Avatar upload failed for user %s: %s',
                   request.user.username, str(e), exc_info=True)
        messages.error(request, 'Avatar upload failed. Please try again.')
        return False


@login_required
def account_view(request):
    """
    User account management page (SOFA refactored).

    Allows authenticated users to update account details.
    GET: Display account management form
    POST: Process account updates via action handlers
    """
    if request.method == 'POST':
        action = request.POST.get('action')

        # Dispatch to action handlers (SOFA - Single Responsibility)
        action_handlers = {
            'update_email': _handle_update_email,
            'update_name': _handle_update_name,
            'update_username': _handle_update_username,
            'update_password': _handle_update_password,
            'update_avatar': _handle_update_avatar,
        }

        handler = action_handlers.get(action)
        if handler:
            handler(request)

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
            logger.warning(
                'Account recovery attempted for non-existent email: %s, IP: %s',
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
            logger.info(
                'Account security change - user: %s, IP: %s, action: password_reset_complete',
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
    selected_language = normalize_language_name(request.GET.get('language', DEFAULT_LANGUAGE))
    user_profile = None
    selected_language_profile = None
    language_profiles = []
    language_profile_map = {}

    if request.user.is_authenticated:
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        language_profiles = list(UserLanguageProfile.objects.filter(user=request.user).order_by('language'))
        language_profile_map = {lp.language: lp for lp in language_profiles}
        selected_language_profile = next(
            (lp for lp in language_profiles if lp.language == selected_language),
            None
        )

    supported_languages = get_supported_languages()
    for entry in supported_languages:
        entry['profile'] = language_profile_map.get(entry['name'])

    context = {
        'user_profile': user_profile,
        'language_profiles': language_profiles,
        'language_profile_map': language_profile_map,
        'selected_language_profile': selected_language_profile,
        'selected_language': selected_language,
        'language_metadata': get_language_metadata(selected_language),
        'supported_languages': supported_languages,
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
    language = normalize_language_name(request.GET.get('language', DEFAULT_LANGUAGE))
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
        'is_guest': not request.user.is_authenticated,
        'speech_code': get_language_metadata(language).get('speech_code', 'en-US'),
    }
    
    return render(request, 'onboarding/quiz.html', context)


def _process_onboarding_answers(answers, attempt):
    """
    Process onboarding answers and calculate score.

    SOFA: Function Extraction - Reduces R0914/R0915 warnings by isolating answer processing.

    Args:
        answers: List of answer dicts from request
        attempt: OnboardingAttempt object

    Returns:
        tuple: (answers_data, total_score, total_possible) or (None, None, None) if error

    Raises:
        OnboardingQuestion.DoesNotExist: If question ID is invalid
    """
    answers_data = []
    total_score = 0
    total_possible = 0

    for answer_item in answers:
        question_id = answer_item.get('question_id')
        user_answer = answer_item.get('answer', '').strip().upper()
        time_taken = answer_item.get('time_taken', 0)

        # Get question (let exception propagate for error handling)
        question = OnboardingQuestion.objects.get(id=question_id)

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

    return answers_data, total_score, total_possible


def _update_onboarding_user_profile(request, attempt, *, calculated_level, total_score, total_possible, answers):
    """
    Update user profile and stats after onboarding completion.

    SOFA: Function Extraction - Reduces R0914/R0915 warnings by isolating profile updates.
    Uses keyword-only arguments to reduce R0917 warning.

    Args:
        request: Django request object
        attempt: OnboardingAttempt object
        calculated_level: (keyword-only) Calculated proficiency level (CEFR string or int)
        total_score: (keyword-only) Total score achieved
        total_possible: (keyword-only) Total possible score
        answers: (keyword-only) List of answer dicts (for time calculation)
    """
    user_profile, _created = UserProfile.objects.get_or_create(user=request.user)
    normalized_language = normalize_language_name(attempt.language)
    
    # Convert CEFR level (A1, A2, B1) to integer (1, 2, 3) if needed
    if isinstance(calculated_level, str):
        cefr_to_level = {'A1': 1, 'A2': 2, 'B1': 3}
        user_profile.proficiency_level = cefr_to_level.get(calculated_level, 1)
    else:
        user_profile.proficiency_level = calculated_level
    
    user_profile.has_completed_onboarding = True
    user_profile.onboarding_completed_at = timezone.now()
    user_profile.target_language = normalized_language
    user_profile.save()

    _upsert_language_onboarding(
        request.user,
        normalized_language,
        calculated_level,
        attempt.completed_at
    )

    # Create QuizResult for stats tracking
    QuizResult.objects.create(
        user=request.user,
        quiz_id=f'onboarding_{attempt.language}',
        quiz_title=f'{attempt.language} Placement Assessment',
        language=normalized_language,
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

    _increment_language_study_stats(
        request.user,
        normalized_language,
        minutes=total_time_minutes,
        quizzes=1
    )

    logger.info('Onboarding completed for user %s: %s (%s/%s)', request.user.username, calculated_level, total_score, total_possible)


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

        # Validate input (SOFA: Early returns for guard clauses)
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

        # Process answers and calculate score (SOFA: Extracted helper)
        try:
            answers_data, total_score, total_possible = _process_onboarding_answers(answers, attempt)
        except OnboardingQuestion.DoesNotExist:
            # Security: Don't expose exception details to external users
            return JsonResponse({'success': False, 'error': 'Invalid question ID'}, status=400)

        # Calculate proficiency level
        calculated_level = OnboardingService().calculate_proficiency_level(answers_data)

        # Update attempt
        attempt.calculated_level = calculated_level
        attempt.total_score = total_score
        attempt.total_possible = total_possible
        attempt.completed_at = timezone.now()
        attempt.save()

        # For authenticated users, update profile AND stats (SOFA: Extracted helper)
        if request.user.is_authenticated:
            _update_onboarding_user_profile(
                request, attempt,
                calculated_level=calculated_level,
                total_score=total_score,
                total_possible=total_possible,
                answers=answers
            )
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
# LESSON VIEWS - DYNAMIC LANGUAGE DETECTION SYSTEM
# =============================================================================
#
# 🤖 AI ASSISTANT INSTRUCTIONS:
# This section implements a fully dynamic lesson system that automatically detects
# and displays lessons for ANY language without hardcoding language names in templates.
#
# ARCHITECTURE OVERVIEW:
# 1. Main lessons page (/lessons/) - Shows language selection buttons
#    - Automatically detects all languages that have published lessons
#    - Displays native language names (e.g., "Español" not "Spanish")
#    - Shows appropriate flag emoji for each language
#
# 2. Language-specific pages (/lessons/spanish/) - Shows lessons for one language
#    - Filters lessons by language parameter
#    - Displays lesson cards with auto-detected topic icons
#    - Fully responsive grid layout
#
# HOW TO ADD A NEW LANGUAGE:
# 1. Add language metadata to home/language_registry.py
# 2. Create lessons in database with language='NewLanguage'
# 3. Page will automatically display new language button
# 4. No template changes needed!
#
# EXAMPLE - Adding Portuguese:
#   LANGUAGE_METADATA = {
#       'Portuguese': {'native_name': 'Português', 'flag': '🇵🇹'},
#       ...
#   }
#   Then create lessons: Lesson.objects.create(title='Colors', language='Portuguese', ...)
#
# DATABASE REQUIREMENTS:
# - Lesson model must have: language (CharField), is_published (BooleanField)
# - Language names must match dictionary keys exactly (case-sensitive)
#
# TEMPLATE VARIABLES PASSED:
# - languages_with_lessons: List of dicts with {name, native_name, flag, lesson_count, lessons}
# - lessons_by_language: Dict of {language: [lessons]} for backward compatibility
# - lessons: QuerySet of all published lessons
#
# =============================================================================

def _build_language_data(language, lessons):
    """
    Helper function to build language data dict with metadata.
    Follows Function Extraction and DRY principles.

    Args:
        language: English language name (e.g., 'Spanish')
        lessons: List of Lesson objects for this language

    Returns:
        Dict with {name, native_name, flag, lesson_count, lessons}
    """
    metadata = get_language_metadata(language)

    return {
        'name': language,
        'native_name': metadata.get('native_name', language),
        'flag': metadata.get('flag', '🌐'),
        'lesson_count': len(lessons),
        'lessons': lessons
    }


def _build_lesson_icon_entries(lessons, user=None):
    """
    Convert a list/queryset of Lesson objects into icon-enriched dicts.
    
    Args:
        lessons: List or QuerySet of Lesson objects
        user: Optional User object to check completion status
    
    Returns:
        list: List of dicts with 'lesson', 'icon', and 'is_complete' keys
    """
    from .models import UserModuleProgress, LearningModule
    
    result = []
    
    # Build a map of lesson completions if user is authenticated
    completion_map = {}
    if user and user.is_authenticated:
        # Get all module progress for lessons we're displaying
        lesson_ids = [lesson.id for lesson in lessons]
        lesson_modules = {}  # Map lesson_id to module
        
        # Get all unique (language, level) combinations from lessons
        lesson_lang_levels = set(
            (lesson.language, lesson.difficulty_level) 
            for lesson in lessons 
            if lesson.skill_category  # Only curriculum lessons are tracked in modules
        )
        
        # Get modules and progress in bulk
        for language, level in lesson_lang_levels:
            try:
                module = LearningModule.objects.get(language=language, proficiency_level=level)
                progress = UserModuleProgress.objects.filter(
                    user=user,
                    module=module
                ).first()
                
                if progress:
                    # Map all lessons in this module to their completion status
                    for lesson in lessons:
                        if (lesson.language == language and 
                            lesson.difficulty_level == level and
                            lesson.skill_category):
                            completion_map[lesson.id] = lesson.id in progress.lessons_completed
            except LearningModule.DoesNotExist:
                pass
    
    for lesson in lessons:
        is_complete = completion_map.get(lesson.id, False)
        result.append({
            'lesson': lesson,
            'icon': _get_lesson_icon(lesson),
            'is_complete': is_complete
        })
    return result


def _organize_lessons_by_level(lesson_entries):
    """
    Organize lessons by level, separating optional lessons (shapes/colors).
    
    Args:
        lesson_entries: List of dicts with 'lesson', 'icon', 'is_complete' keys
    
    Returns:
        dict: {
            'levels': [
                {'level': 1, 'lessons': [...]},
                {'level': 2, 'lessons': [...]},
                ...
            ],
            'optional_lessons': [...]
        }
    """
    # Separate optional lessons (shapes and colors)
    optional_lessons = []
    regular_lessons = []
    
    for entry in lesson_entries:
        lesson = entry['lesson']
        # Check if slug starts with 'shapes' or 'colors' (handles 'shapes', 'shapes-french', etc.)
        if lesson.slug and (lesson.slug.startswith('shapes') or lesson.slug.startswith('colors')):
            optional_lessons.append(entry)
        else:
            regular_lessons.append(entry)
    
    # Group regular lessons by level
    lessons_by_level = defaultdict(list)
    for entry in regular_lessons:
        level = entry['lesson'].difficulty_level or 1
        lessons_by_level[level].append(entry)
    
    # Sort levels and build structure
    sorted_levels = sorted(lessons_by_level.keys())
    levels = [{'level': level, 'lessons': lessons_by_level[level]} for level in sorted_levels]
    
    return {
        'levels': levels,
        'optional_lessons': optional_lessons
    }


def _get_user_language_context(request):
    """
    Get user profile and language context for lessons view.

    SOFA: Function Extraction - Reduces R0914 warning by isolating profile logic.

    Args:
        request: Django request object

    Returns:
        tuple: (language_profile_map, current_language_profile, current_language, user_profile)
    """
    language_profile_map = {}
    current_language_profile = None
    current_language = DEFAULT_LANGUAGE
    user_profile = None

    if not request.user.is_authenticated:
        return language_profile_map, current_language_profile, current_language, user_profile

    # Get user profile and target language
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.target_language:
            current_language = normalize_language_name(user_profile.target_language)
    except UserProfile.DoesNotExist:
        pass

    # Build language profile map
    user_language_profiles = list(UserLanguageProfile.objects.filter(user=request.user))
    language_profile_map = {lp.language: lp for lp in user_language_profiles}
    current_language_profile = language_profile_map.get(current_language)

    # Prefer first completed onboarding language as default if target not ready
    completed_languages = [lp.language for lp in user_language_profiles if lp.has_completed_onboarding]
    if completed_languages and (not current_language_profile or not current_language_profile.has_completed_onboarding):
        current_language = completed_languages[0]
        current_language_profile = language_profile_map.get(current_language)

    return language_profile_map, current_language_profile, current_language, user_profile


def _build_language_dropdown(grouped_lessons, language_profile_map, selected_language, lessons_base_url, is_authenticated):
    """
    Build language dropdown menu for lessons view.

    SOFA: Function Extraction - Reduces R0914 warning by isolating dropdown logic.

    Args:
        grouped_lessons: Dict mapping language names to lesson lists
        language_profile_map: Dict mapping language names to UserLanguageProfile objects
        selected_language: Currently selected language name
        lessons_base_url: Base URL for lessons list
        is_authenticated: Whether user is authenticated

    Returns:
        list: List of dicts with language dropdown data
    """
    language_dropdown = []
    for language_name, _lessons in grouped_lessons.items():
        metadata = get_language_metadata(language_name)
        profile = language_profile_map.get(language_name)
        locked = not (is_authenticated and profile and profile.has_completed_onboarding)
        language_dropdown.append({
            'name': language_name,
            'native_name': metadata.get('native_name', language_name),
            'flag': metadata.get('flag', '🌐'),
            'url': f"{lessons_base_url}?language={language_name}",
            'locked': locked,
            'is_active': language_name == selected_language,
        })
    return language_dropdown


def lessons_list(request):
    """
    Display lessons for the user's selected language with inline navigation.
    
    Filters lessons based on user's current level:
    - Shows all lessons for current level
    - Shows completed lessons from previous levels
    - Hides lessons from future levels
    """
    # Get all published lessons grouped by language for dropdown + rendering
    all_lessons = Lesson.objects.filter(is_published=True).order_by('language', 'order', 'id')
    grouped_lessons = defaultdict(list)
    for lesson in all_lessons:
        grouped_lessons[lesson.language].append(lesson)

    languages_with_lessons = [
        _build_language_data(language, lessons)
        for language, lessons in grouped_lessons.items()
    ]

    # Get user language context (SOFA: Extracted helper)
    language_profile_map, current_language_profile, current_language, _ = _get_user_language_context(request)
    
    # Determine which language to display (query param overrides default)
    requested_language = request.GET.get('language')
    if requested_language:
        selected_language = normalize_language_name(requested_language)
    else:
        selected_language = current_language
    
    # Fallback if no lessons exist for the requested language
    if selected_language not in grouped_lessons and grouped_lessons:
        selected_language = next(iter(grouped_lessons.keys()))
    
    # Get selected language profile for context
    selected_language_profile = language_profile_map.get(selected_language)
    
    # Filter lessons based on user level
    selected_language_lessons_list = grouped_lessons.get(selected_language, [])
    if request.user.is_authenticated:
        # Convert list to QuerySet for filtering
        lesson_ids = [lesson.id for lesson in selected_language_lessons_list]
        lessons_qs = Lesson.objects.filter(id__in=lesson_ids, is_published=True)
        filtered_lessons = _filter_lessons_by_user_level(lessons_qs, request.user, selected_language)
        selected_language_lessons_list = list(filtered_lessons.order_by('order', 'id'))
    
    # Get progress information for current level
    module_progress = None
    test_progress = None
    if request.user.is_authenticated and selected_language_profile:
        from .models import LearningModule, UserModuleProgress
        
        # Get user's current level
        current_level = 1
        if selected_language_profile.proficiency_level:
            prof_level = selected_language_profile.proficiency_level
            if isinstance(prof_level, str):
                cefr_to_level = {'A1': 1, 'A2': 2, 'B1': 3}
                current_level = cefr_to_level.get(prof_level, 1)
            else:
                try:
                    current_level = int(prof_level)
                except (ValueError, TypeError):
                    current_level = 1
        
        # Get module progress for current level
        try:
            module = LearningModule.objects.get(
                language=selected_language,
                proficiency_level=current_level
            )
            progress, _ = UserModuleProgress.objects.get_or_create(
                user=request.user,
                module=module
            )
            module_progress = progress
            
            # Calculate test progress (completed lessons / 5)
            required_lessons = module.get_lessons()
            completed_count = sum(1 for lesson in required_lessons if lesson.id in progress.lessons_completed)
            test_progress = {
                'completed': completed_count,
                'total': 5,
                'percentage': (completed_count / 5 * 100) if completed_count > 0 else 0,
                'can_take_test': progress.all_lessons_completed(),
                'is_module_complete': progress.is_module_complete,
                'current_level': current_level,
            }
        except LearningModule.DoesNotExist:
            pass
    
    # Build language dropdown (SOFA: Extracted helper, inline base URL to reduce R0914)
    language_dropdown = _build_language_dropdown(
        grouped_lessons,
        language_profile_map,
        selected_language,
        reverse('lessons_list'),
        request.user.is_authenticated
    )
    # Build lesson entries and organize by level
    lesson_entries = _build_lesson_icon_entries(selected_language_lessons_list, request.user)
    organized_lessons = _organize_lessons_by_level(lesson_entries)
    
    context = {
        'languages_with_lessons': languages_with_lessons,
        'language_dropdown': language_dropdown,
        'selected_language': selected_language,
        'selected_language_metadata': get_language_metadata(selected_language),
        'selected_language_profile': selected_language_profile,
        'selected_language_lessons': lesson_entries,  # Keep for backward compatibility if needed
        'organized_lessons': organized_lessons,  # New organized structure
        'selected_language_completed': bool(
            request.user.is_authenticated and selected_language_profile and selected_language_profile.has_completed_onboarding
        ),
        'selected_language_has_lessons': bool(selected_language_lessons_list),
        'current_language_name': current_language,
        'current_language_profile': current_language_profile,
        'current_language_metadata': get_language_metadata(current_language),
        'module_progress': module_progress,
        'test_progress': test_progress,
    }
    return render(request, 'lessons_list.html', context)


def lessons_by_language(request, language):
    """
    Display lessons for a specific language (e.g., /lessons/spanish/).

    🤖 AI ASSISTANT INSTRUCTIONS:
    This view handles language-specific lesson pages. It receives a language
    name from the URL (lowercase) and displays lessons for that language,
    filtered by user's current level.

    URL PATTERN: lessons/<str:language>/ (defined in home/urls.py)
    EXAMPLE URLs: /lessons/spanish/, /lessons/french/, /lessons/german/

    ⚠️ CRITICAL URL ROUTING REQUIREMENT:
    In home/urls.py, this pattern MUST come AFTER lessons/<int:lesson_id>/
    Otherwise, numeric lesson IDs will be interpreted as language names!

    CORRECT ORDER in urls.py:
      1. path("lessons/<int:lesson_id>/", ...)      ← FIRST (specific)
      2. path("lessons/<str:language>/", ...)       ← SECOND (general)

    WRONG ORDER causes bugs like /lessons/2/ being treated as language "2"!

    HOW IT WORKS:
    1. Receives language from URL (e.g., 'spanish')
    2. Capitalizes it to match database format (e.g., 'Spanish')
    3. Queries all published lessons with that language
    4. Filters by user's current level (shows current + completed previous)
    5. Orders by lesson.order field, then by ID
    6. Passes lessons to template

    TEMPLATE: home/templates/lessons/lessons_by_language.html
    - Displays lesson cards in a grid
    - Auto-detects lesson icons based on title/slug
    - Shows lesson count, difficulty badges, flashcard counts

    TO ADD NEW LESSONS TO EXISTING LANGUAGE:
    Just create lesson in database with matching language name:
        Lesson.objects.create(
            title='Numbers in Spanish',
            language='Spanish',
            slug='numbers',
            is_published=True,
            order=3
        )
    This view will automatically include it - no code changes needed!
    """
    # Validate language parameter to prevent SQL injection and invalid input
    # Language names should only contain letters, spaces, and hyphens
    # Note: re already imported at module level (no shadowing - SOFA principle)
    if not re.match(r'^[a-zA-Z\s\-]+$', language):
        # Invalid characters detected (e.g., SQL injection attempt)
        raise Http404("Invalid language parameter")

    # Normalize to match metadata/database format
    language = normalize_language_name(language)
    
    # Check if user is authenticated and has completed onboarding for this language
    has_completed_onboarding = False
    language_profile = None
    if request.user.is_authenticated:
        try:
            language_profile = UserLanguageProfile.objects.get(
                user=request.user, 
                language=language
            )
            has_completed_onboarding = language_profile.has_completed_onboarding
        except UserLanguageProfile.DoesNotExist:
            has_completed_onboarding = False
    
    # Get language metadata
    language_metadata = get_language_metadata(language)

    # Get lessons for the specified language
    lessons = Lesson.objects.filter(
        language=language,
        is_published=True
    ).order_by('order', 'id')
    
    # Filter lessons based on user level
    if request.user.is_authenticated:
        lessons = _filter_lessons_by_user_level(lessons, request.user, language)

    lessons_with_icons = _build_lesson_icon_entries(lessons)

    context = {
        'language': language,
        'language_metadata': language_metadata,
        'lessons_with_icons': lessons_with_icons,
        'has_completed_onboarding': has_completed_onboarding,
        'language_profile': language_profile,
    }

    return render(request, 'lessons/lessons_by_language.html', context)


def _get_lesson_icon(lesson):
    """
    Helper function to determine lesson icon based on topic.

    SOFA Principles Applied:
    - Open/Closed: Dictionary mapping allows extension without modification
    - Avoid Repetition: Single loop replaces 12 if statements
    - Single Responsibility: Only determines icon, nothing else

    Returns icon emoji based on lesson topic keywords.
    """
    # SOFA: Open/Closed - Dictionary mapping (extensible without modification)
    lesson_icon_map = {
        'color': '🎨',
        'shape': '🔷',
        'number': '🔢',
        'animal': '🐾',
        'food': '🍎',
        'family': '👨‍👩‍👧‍👦',
        'greeting': '👋',
        'verb': '⚡',
        'adjective': '✨',
        'time': '🕐',
        'weather': '🌤️',
        'clothing': '👕',
        'body': '👤',
        'house': '🏠',
        'home': '🏠',
        'room': '🚪',
        'school': '🏫',
        'work': '💼',
        'job': '💼',
        'travel': '✈️',
        'transport': '🚗',
        'car': '🚗',
        'bus': '🚌',
        'train': '🚂',
        'plane': '✈️',
        'sport': '⚽',
        'sports': '⚽',
        'music': '🎵',
        'movie': '🎬',
        'film': '🎬',
        'book': '📖',
        'reading': '📖',
        'shopping': '🛒',
        'store': '🛒',
        'restaurant': '🍽️',
        'cafe': '☕',
        'drink': '🥤',
        'fruit': '🍊',
        'vegetable': '🥕',
        'nature': '🌳',
        'tree': '🌳',
        'flower': '🌸',
        'country': '🌍',
        'city': '🏙️',
        'place': '📍',
        'direction': '🧭',
        'emotion': '😊',
        'feeling': '😊',
        'health': '🏥',
        'doctor': '🏥',
        'hospital': '🏥',
        'hobby': '🎨',
        'activity': '🎯',
        'day': '☀️',
        'night': '🌙',
        'season': '🍂',
        'month': '📅',
        'week': '📆',
        'grammar': '📝',
        'vocabulary': '📚',
        'pronunciation': '🗣️',
        'conversation': '💬',
        'question': '❓',
        'answer': '💡',
    }

    slug = (lesson.slug or '').lower()
    title = lesson.title.lower()

    # SOFA: DRY - Single loop replaces duplicate if statements
    # Check for exact matches first, then partial matches
    for keyword, icon in lesson_icon_map.items():
        if keyword in slug or keyword in title:
            return icon

    return '📚'  # Default icon


def lesson_detail(request, lesson_id):
    """Display lesson detail with flashcards."""
    lesson = get_object_or_404(Lesson, id=lesson_id, is_published=True)
    cards = lesson.cards.all()
    metadata = get_language_metadata(lesson.language)
    context = {
        'lesson': lesson,
        'cards': cards,
        'speech_code': metadata.get('speech_code', 'en-US'),
    }
    return render(request, 'lessons/lesson_detail.html', context)


def lesson_quiz(request, lesson_id):
    """Display quiz for a specific lesson."""
    lesson = get_object_or_404(Lesson, id=lesson_id, is_published=True)
    questions = lesson.quiz_questions.all()
    qlist = []
    for q in questions:
        indexed_options = list(enumerate(q.options or []))
        random.shuffle(indexed_options)
        shuffled_options = [
            {
                'text': option_text,
                'index': original_index,
            }
            for original_index, option_text in indexed_options
        ]
        qlist.append({
            'id': q.id,
            'order': q.order,
            'question': q.question,
            'options': shuffled_options,
        })
    metadata = get_language_metadata(lesson.language)
    context = {
        'lesson': lesson,
        'questions': qlist,
        'speech_code': metadata.get('speech_code', 'en-US'),
    }

    # Build template candidates - curriculum lessons use generic template
    template_candidates = []
    
    # If lesson has skill_category, it's a curriculum lesson - use generic template
    if lesson.skill_category:
        template_candidates.append('curriculum/lesson_quiz.html')
    
    # Also try slug-based templates for backward compatibility (old lessons)
    if lesson.slug:
        template_candidates.append(f'lessons/{lesson.slug}/quiz.html')
        if '-' in lesson.slug:
            base_slug = lesson.slug.split('-')[0]
            template_candidates.append(f'lessons/{base_slug}/quiz.html')
    
    # Always include generic fallback as last resort
    template_candidates.append('curriculum/lesson_quiz.html')

    try:
        template = select_template(template_candidates)
        template_name = template.template.name
    except TemplateDoesNotExist as exc:
        # SOFA: Proper exception chaining preserves debugging context
        raise Http404("Lesson quiz template is missing. Please contact support.") from exc

    return render(request, template_name, context)


def _evaluate_lesson_quiz_answers(answers, lesson):
    """
    Evaluate lesson quiz answers and calculate score.

    SOFA: Function Extraction - Reduces R0914/R0915/R0912 warnings by isolating answer evaluation.

    Args:
        answers: List of answer dicts from request
        lesson: Lesson object

    Returns:
        tuple: (score, total) - number correct and total questions answered
    """
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

    return score, total


def _update_lesson_quiz_user_stats(request, lesson, score, total):
    """
    Update user stats and award XP after lesson quiz completion.

    SOFA: Function Extraction - Reduces R0914/R0915/R0912 warnings by isolating stats updates.

    Args:
        request: Django request object
        lesson: Lesson object
        score: Quiz score
        total: Total questions

    Returns:
        tuple: (xp_result, language_xp_result) - XP award results or (None, None)
    """
    # Create QuizResult for stats tracking
    QuizResult.objects.create(
        user=request.user,
        quiz_id=f'lesson_{lesson.id}',
        quiz_title=lesson.title,
        language=lesson.language,
        score=score,
        total_questions=total
    )

    # Create LessonCompletion record
    LessonCompletion.objects.create(
        user=request.user,
        lesson_id=str(lesson.id),
        lesson_title=lesson.title,
        language=lesson.language,
        duration_minutes=5  # Estimated time per lesson quiz
    )

    # Award XP for lesson completion (Sprint 3 - Issue #17)
    base_xp = 50  # Base XP per lesson
    bonus_xp = 10 if total > 0 and score == total else 0  # Bonus for perfect score
    total_xp_awarded = base_xp + bonus_xp

    # Safely get or create profile (defensive programming)
    normalized_language = normalize_language_name(lesson.language)
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
        logger.warning('UserProfile was missing for user %s, created new profile', request.user.username)

    # Award XP with error handling
    xp_result = None
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

    language_xp_result = _award_language_xp(request.user, lesson.language, total_xp_awarded)

    if profile.target_language != normalized_language:
        profile.target_language = normalized_language
        profile.save(update_fields=['target_language'])

    # Update UserProgress
    user_progress, _ = UserProgress.objects.get_or_create(user=request.user)
    user_progress.total_quizzes_taken += 1
    user_progress.total_lessons_completed += 1
    user_progress.overall_quiz_accuracy = user_progress.calculate_quiz_accuracy()
    user_progress.update_streak()  # Update streak when lesson completed
    user_progress.save()

    _increment_language_study_stats(
        request.user,
        lesson.language,
        minutes=5,
        lessons=1,
        quizzes=1
    )

    logger.info('Lesson quiz completed: %s - %s: %s/%s', request.user.username, lesson.title, score, total)

    return xp_result, language_xp_result


def _build_lesson_quiz_response(request, lesson, attempt, *, score, total, xp_result, language_xp_result):
    """
    Build JSON or redirect response for lesson quiz submission.

    SOFA: Function Extraction - Reduces R0914/R0912 warnings by isolating response building.
    Uses keyword-only arguments to reduce R0917 warning.

    Args:
        request: Django request object
        lesson: Lesson object
        attempt: LessonAttempt object
        score: (keyword-only) Quiz score
        total: (keyword-only) Total questions
        xp_result: (keyword-only) XP award result dict or None
        language_xp_result: (keyword-only) Language XP award result dict or None

    Returns:
        HttpResponse: JsonResponse or redirect
    """
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
            if language_xp_result:
                response_data['language_xp'] = {
                    'language': lesson.language,
                    'awarded': language_xp_result['xp_awarded'],
                    'total': language_xp_result['total_xp'],
                    'leveled_up': language_xp_result['leveled_up'],
                    'new_level': language_xp_result['new_level'],
                }

        return JsonResponse(response_data)
    return redirect('lesson_results', lesson_id=lesson.id, attempt_id=attempt.id)


@require_http_methods(["POST"])
def submit_lesson_quiz(request, lesson_id):
    """Process lesson quiz submission."""
    lesson = get_object_or_404(Lesson, id=lesson_id, is_published=True)

    # Initialize XP result variables (defensive programming - SOFA: Single Responsibility)
    xp_result = None
    language_xp_result = None

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

    # Evaluate answers (SOFA: Extracted helper)
    score, total = _evaluate_lesson_quiz_answers(answers, lesson)

    # Create attempt record
    attempt = LessonAttempt.objects.create(
        lesson=lesson,
        user=request.user if request.user.is_authenticated else None,
        score=score,
        total=total
    )

    # Track stats for authenticated users (SOFA: Extracted helper)
    xp_result = None
    language_xp_result = None
    if request.user.is_authenticated:
        xp_result, language_xp_result = _update_lesson_quiz_user_stats(request, lesson, score, total)

    # Build response (SOFA: Extracted helper)
    return _build_lesson_quiz_response(
        request, lesson, attempt,
        score=score,
        total=total,
        xp_result=xp_result,
        language_xp_result=language_xp_result
    )


def lesson_results(request, lesson_id, attempt_id):
    """Display results for a completed lesson quiz."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    attempt = get_object_or_404(LessonAttempt, id=attempt_id, lesson=lesson)
    next_lesson = lesson.next_lesson
    context = {'lesson': lesson, 'attempt': attempt, 'next_lesson': next_lesson}
    template_candidates = [f'lessons/{lesson.slug}/results.html']
    if '-' in (lesson.slug or ''):
        base_slug = lesson.slug.split('-')[0]
        template_candidates.append(f'lessons/{base_slug}/results.html')

    try:
        template = select_template(template_candidates)
        template_name = template.template.name
    except TemplateDoesNotExist as exc:
        # SOFA: Proper exception chaining preserves debugging context
        raise Http404("Lesson results template is missing. Please contact support.") from exc

    return render(request, template_name, context)


# =============================================================================
# DAILY QUEST VIEWS (Sprint 3 - Issue #18)
# =============================================================================

@login_required
def daily_quest_view(request):
    """
    Display today's five-question challenge and progress overview.
    """
    try:
        challenge = DailyQuestService.get_today_challenge(request.user)
        weekly_stats = DailyQuestService.get_weekly_stats(request.user)
        lifetime_stats = DailyQuestService.get_lifetime_stats(request.user)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error('Failed to load daily challenge page: %s', exc, exc_info=True)
        challenge = None
        weekly_stats = {'challenges_completed': 0, 'xp_earned': 0, 'accuracy': 0}
        lifetime_stats = {'challenges_completed': 0, 'xp_earned': 0, 'accuracy': 0}

    context = {
        'challenge': challenge,
        'weekly_stats': weekly_stats,
        'lifetime_stats': lifetime_stats,
    }
    return render(request, 'home/daily_quest.html', context)


@login_required
@require_POST
def daily_quest_submit(request):
    """
    Grade the user's answers and award XP.
    """
    try:
        result = DailyQuestService.submit_challenge(request.user, request.POST)
    except ValueError as exc:
        messages.error(request, str(exc))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error('Failed to submit daily challenge: %s', exc, exc_info=True)
        messages.error(request, 'We could not grade your challenge. Please try again.')
    else:
        if result.get('already_completed'):
            messages.info(request, 'Challenge already completed—come back tomorrow for a new one!')
        else:
            correct = result['correct']
            total = result['total']
            xp = result['xp_awarded']
            messages.success(request, f'Challenge completed! You scored {correct}/{total} and earned {xp} XP.')
    return redirect('daily_quest')


@login_required
def quest_history(request):
    """
    Show history of completed daily challenges.
    """
    attempts = UserDailyQuestAttempt.objects.filter(
        user=request.user,
        is_completed=True
    ).select_related('daily_quest', 'daily_quest__based_on_lesson').order_by(
        '-daily_quest__date',
        '-completed_at'
    )
    total_quest_xp = attempts.aggregate(total=Sum('xp_earned'))['total'] or 0

    context = {
        'attempts': attempts,
        'total_quest_xp': total_quest_xp,
    }
    return render(request, 'home/quest_history.html', context)

@require_http_methods(["POST"])
def generate_onboarding_speech(request):
    """Generate speech using OpenAI TTS (primary) with ElevenLabs fallback"""
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        lang = data.get('lang', 'es-ES')

        if not text:
            return HttpResponse("No text provided", status=400)

        # Clean text - remove parentheses
        while '(' in text:
            start = text.find('(')
            end = text.find(')', start)
            if end == -1:
                break
            text = text[:start] + ' ' + text[end+1:]
        text = ' '.join(text.split()).strip()

        # Add buffer at beginning to prevent browser audio cutoff
        # The browser often cuts off first 100-200ms, so we add disposable content
        text = 'Okay. ' + text

        # Try OpenAI TTS first (primary)
        openai_key = settings.OPENAI_API_KEY
        if openai_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)

                # Choose voice and speed based on language
                # For Spanish: use "alloy" (neutral, clearer) and slower speed
                # For English: use "alloy" at normal speed
                if 'es' in lang.lower():
                    voice = "alloy"
                    speed = 0.85  # Slower for Spanish pronunciation
                else:
                    voice = "alloy"
                    speed = 1.0  # Normal speed for English

                # Log the text being sent for debugging
                logger.info("OpenAI TTS: lang=%s, voice=%s, speed=%s, text='%s'", lang, voice, speed, text)

                response = client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=text,
                    speed=speed
                )

                audio_bytes = response.content
                return HttpResponse(audio_bytes, content_type='audio/mpeg')

            except (RuntimeError, ValueError, ConnectionError, OSError) as e:
                logger.warning("OpenAI TTS failed, trying ElevenLabs fallback: %s", str(e))

        # Fallback to ElevenLabs
        elevenlabs_key = settings.ELEVENLABS_API_KEY
        if elevenlabs_key:
            try:
                from elevenlabs.client import ElevenLabs  # pylint: disable=import-error,import-outside-toplevel
                client = ElevenLabs(api_key=elevenlabs_key)

                # Choose voice based on language
                if 'es' in lang.lower():
                    voice_id = "pFZP5JQG7iQjIQuC4Bku"  # Lily - female Spanish
                else:
                    voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel - English female

                audio = client.text_to_speech.convert(
                    voice_id=voice_id,
                    text=text,
                    model_id="eleven_multilingual_v2"
                )

                audio_bytes = b''.join(audio)
                return HttpResponse(audio_bytes, content_type='audio/mpeg')

            except (RuntimeError, ValueError, ConnectionError, OSError) as e:
                logger.error("ElevenLabs TTS also failed: %s", str(e))

        # Both TTS services unavailable
        return HttpResponse("TTS not available", status=503)

    except (RuntimeError, ValueError, TypeError, ConnectionError, OSError) as e:
        # Log the detailed error for debugging (SOFA: DRY - logging already imported at module level)
        # Use lazy % formatting for performance (STYLE_GUIDE.md)
        logger.error("TTS Error: %s", str(e))

        # Return generic error to user (don't expose internal details)
        return HttpResponse("Text-to-speech generation failed", status=500)


# ============================================
# HELP/WIKI SYSTEM VIEWS
# ============================================

def help_page(request):
    """
    Display help/wiki documentation page.

    Accessible to all users (guest, logged-in, admin).
    - Regular users: See User Guide only
    - Admin users: See both User Guide + Admin Guide tabs

    SOFA Principles:
    - Single Responsibility: Render help page with appropriate documentation
    - Function Extraction: Documentation loading delegated to HelpService
    - DRY: Reusable service for both User and Admin guides

    Args:
        request: HTTP request object

    Returns:
        HttpResponse: Rendered help page template
    """
    # Determine if user is admin (access control)
    is_admin = request.user.is_authenticated and request.user.is_staff

    # Load User Guide (available to all users)
    user_guide = HelpService.load_user_guide()

    # Load Admin Guide only for admin users (access control)
    admin_guide = HelpService.load_admin_guide() if is_admin else None

    context = {
        'is_admin': is_admin,
        'user_guide': user_guide,
        'admin_guide': admin_guide,
    }

    return render(request, 'home/help.html', context)


@require_POST
def chatbot_query(request):
    """
    API endpoint for chatbot queries.

    Accepts POST requests with JSON body containing:
    - query: User's question (required)
    - chat_history: Previous conversation messages (optional)

    Returns JSON response with:
    - response: AI-generated answer
    - sources: Relevant documentation sections

    SOFA Principles:
    - Single Responsibility: Handle API request/response, delegate to service
    - Function Extraction: AI logic in ChatbotService
    - DRY: Reusable service for chatbot interactions

    Access: Available to all users (guest, logged-in, admin)
    Method: POST only
    Content-Type: application/json
    """
    try:
        # Parse JSON request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {'error': 'Invalid JSON in request body'},
                status=400
            )

        # Validate required parameters
        query = data.get('query', '').strip()
        if not query:
            return JsonResponse(
                {'error': 'Query parameter is required'},
                status=400
            )

        # Get optional chat history
        chat_history = data.get('chat_history', [])

        # Determine user role for documentation access
        user_role = 'admin' if (request.user.is_authenticated and request.user.is_staff) else 'user'

        # Get AI response from ChatbotService
        result = ChatbotService.get_ai_response(
            query=query,
            user_role=user_role,
            chat_history=chat_history
        )

        return JsonResponse(result, status=200)

    except (RuntimeError, ValueError, TypeError, KeyError, ConnectionError) as e:
        # Log error securely - don't expose exception details to users
        logger.error('Chatbot API error: %s', type(e).__name__)

        return JsonResponse(
            {'error': 'An error occurred while processing your request'},
            status=500
        )


# ============================================
# CURRICULUM SYSTEM VIEWS
# ============================================

@login_required
def curriculum_overview(request, language):
    """
    Display all 10 levels for a language curriculum.
    
    Shows level progress, completion status, and navigation to each module.
    
    Args:
        request: HTTP request object
        language: Target language (e.g., 'Spanish', 'French')
    
    Returns:
        HttpResponse: Rendered curriculum overview template
    """
    from .models import LearningModule, UserModuleProgress
    
    # Normalize language name
    language = language.strip().title()
    
    # Get all modules for this language
    modules = LearningModule.objects.filter(
        language=language
    ).order_by('proficiency_level')
    
    if not modules.exists():
        messages.info(request, f'No curriculum available for {language} yet.')
        return redirect('lessons_list')
    
    # Get user's progress for each module
    user_progress = {
        p.module_id: p for p in UserModuleProgress.objects.filter(
            user=request.user,
            module__language=language
        ).select_related('module')
    }
    
    # Build module data with progress
    module_data = []
    for module in modules:
        progress = user_progress.get(module.id)
        module_data.append({
            'module': module,
            'progress': progress,
            'lessons_completed': len(progress.lessons_completed) if progress else 0,
            'is_complete': progress.is_module_complete if progress else False,
            'best_score': progress.best_test_score if progress else 0,
            'is_locked': module.proficiency_level > 1 and not _is_previous_level_complete(
                user_progress, language, module.proficiency_level
            ),
        })
    
    # Get user's current level for this language
    lang_profile = UserLanguageProfile.objects.filter(
        user=request.user,
        language=language
    ).first()
    current_level = lang_profile.proficiency_level if lang_profile else 1
    
    context = {
        'language': language,
        'modules': module_data,
        'current_level': current_level,
    }
    
    return render(request, 'curriculum/overview.html', context)


def _is_previous_level_complete(user_progress: dict, language: str, level: int) -> bool:
    """Check if the previous level is complete."""
    if level <= 1:
        return True
    
    for module_id, progress in user_progress.items():
        if (progress.module.language == language and 
            progress.module.proficiency_level == level - 1):
            return progress.is_module_complete
    
    return False


def _filter_lessons_by_user_level(lessons, user, language):
    """
    Filter lessons based on user's current level and completion status.
    
    Rules:
    - Show all lessons for user's current level
    - Show completed lessons from previous levels
    - Hide lessons from future levels
    - Always show shapes and colors if they're level 1
    
    Args:
        lessons: QuerySet of Lesson objects
        user: User object (can be AnonymousUser)
        language: Target language
        
    Returns:
        QuerySet: Filtered lessons
    """
    from .models import UserLanguageProfile, UserModuleProgress, LearningModule
    
    if not user.is_authenticated:
        # For anonymous users, only show level 1 lessons
        return lessons.filter(difficulty_level=1)
    
    # Get user's current level for this language
    lang_profile = UserLanguageProfile.objects.filter(
        user=user,
        language=language
    ).first()
    
    # Ensure current_level is always an integer (default to 1 if None)
    # Handle legacy CEFR string values (A1, A2, B1) by converting to integers
    if lang_profile and lang_profile.proficiency_level is not None:
        prof_level = lang_profile.proficiency_level
        # If it's a string (legacy CEFR format), convert it
        if isinstance(prof_level, str):
            cefr_to_level = {'A1': 1, 'A2': 2, 'B1': 3}
            current_level = cefr_to_level.get(prof_level, 1)
        else:
            # It's already an integer or can be converted
            try:
                current_level = int(prof_level)
            except (ValueError, TypeError):
                current_level = 1
    else:
        current_level = 1
    
    # Get all completed lesson IDs across all levels for this language
    completed_lesson_ids = set()
    user_progress = UserModuleProgress.objects.filter(
        user=user,
        module__language=language
    ).select_related('module')
    
    for progress in user_progress:
        completed_lesson_ids.update(progress.lessons_completed)
    
    # Filter lessons:
    # 1. Current level lessons (always visible)
    # 2. Previous level lessons that are completed
    # 3. Shapes and colors if level 1 (always visible at level 1+)
    filtered_lessons = []
    for lesson in lessons:
        # Ensure difficulty_level is an integer (handle any legacy string values)
        try:
            lesson_level = int(lesson.difficulty_level) if lesson.difficulty_level is not None else 1
        except (ValueError, TypeError):
            # If difficulty_level is invalid, default to 1
            lesson_level = 1
        
        # Check if this is a shapes/colors lesson (handles 'shapes', 'shapes-french', etc.)
        is_shapes_colors = lesson.slug and (lesson.slug.startswith('shapes') or lesson.slug.startswith('colors'))
        
        if is_shapes_colors and lesson_level == 1:
            # Always show shapes/colors if user is at least level 1
            if current_level >= 1:
                filtered_lessons.append(lesson.id)
        elif lesson_level == current_level:
            # Always show current level lessons
            filtered_lessons.append(lesson.id)
        elif lesson_level < current_level:
            # Show previous level lessons only if completed
            if lesson.id in completed_lesson_ids:
                filtered_lessons.append(lesson.id)
    
    return lessons.filter(id__in=filtered_lessons)


def _get_level_1_special_lessons(language):
    """
    Get shapes and colors lessons for level 1.
    
    These are special lessons that should always appear in level 1
    alongside the 5 skill-based lessons.
    
    Args:
        language: Target language
        
    Returns:
        QuerySet: Shapes and colors lessons for this language at level 1
    """
    from .models import Lesson
    
    return Lesson.objects.filter(
        language=language,
        difficulty_level=1,
        is_published=True
    ).filter(
        Q(slug__startswith='shapes') | Q(slug__startswith='colors')
    ).order_by('order', 'id')


@login_required
def module_detail(request, language, level):
    """
    Display a learning module with its 5 lessons and test access.
    
    Shows lesson completion status and enables test-taking when ready.
    For level 1, also includes shapes and colors lessons.
    
    Args:
        request: HTTP request object
        language: Target language
        level: Proficiency level (1-10)
    
    Returns:
        HttpResponse: Rendered module detail template
    """
    from .models import LearningModule, UserModuleProgress, SkillCategory
    
    language = language.strip().title()
    
    # Get the module
    module = get_object_or_404(
        LearningModule,
        language=language,
        proficiency_level=level
    )
    
    # Get user's progress
    progress, _ = UserModuleProgress.objects.get_or_create(
        user=request.user,
        module=module
    )
    
    # Get lessons for this module with completion status
    lessons = module.get_lessons()
    lesson_data = []
    for lesson in lessons:
        lesson_data.append({
            'lesson': lesson,
            'is_complete': lesson.id in progress.lessons_completed,
            'skill_icon': lesson.skill_category.icon if lesson.skill_category else '📚',
            'skill_name': lesson.skill_category.get_name_display() if lesson.skill_category else 'Unknown',
        })
    
    # For level 1, also include optional lessons
    if level == 1:
        special_lessons = _get_level_1_special_lessons(language)
        for lesson in special_lessons:
            # Check if already in lesson_data (shouldn't happen, but safe)
            if not any(item['lesson'].id == lesson.id for item in lesson_data):
                lesson_data.append({
                    'lesson': lesson,
                    'is_complete': lesson.id in progress.lessons_completed,
                    'skill_icon': _get_lesson_icon(lesson),
                    'skill_name': lesson.title.replace(f' in {language}', '').replace(f' in {language.title()}', ''),
                })
        # Sort by order to maintain proper sequence
        lesson_data.sort(key=lambda x: (x['lesson'].order, x['lesson'].id))
    
    # Check if test is available
    test_service = AdaptiveTestService()
    test_status = test_service.can_take_test(request.user, module)
    
    # Calculate progress toward test (only count the 5 required skill-based lessons)
    required_lessons = module.get_lessons()
    completed_required = sum(1 for lesson in required_lessons if lesson.id in progress.lessons_completed)
    lessons_remaining = max(0, 5 - completed_required)
    
    context = {
        'language': language,
        'level': level,
        'module': module,
        'progress': progress,
        'lessons': lesson_data,
        'can_take_test': test_status['can_take'],
        'test_status_reason': test_status['reason'],
        'retry_available_at': test_status.get('retry_available_at'),
        'completed_required': completed_required,
        'lessons_remaining': lessons_remaining,
    }
    
    return render(request, 'curriculum/module_detail.html', context)


@login_required
def lesson_by_skill(request, language, level, skill):
    """
    Display a lesson by skill category within a level.
    
    Args:
        request: HTTP request object
        language: Target language
        level: Proficiency level (1-10)
        skill: Skill category (vocabulary, grammar, etc.)
    
    Returns:
        HttpResponse: Rendered lesson template
    """
    from .models import SkillCategory, UserModuleProgress, LearningModule
    
    language = language.strip().title()
    skill = skill.strip().lower()
    
    # Get the skill category
    skill_category = get_object_or_404(SkillCategory, name=skill)
    
    # Get the lesson
    lesson = get_object_or_404(
        Lesson,
        language=language,
        difficulty_level=level,
        skill_category=skill_category,
        is_published=True
    )
    
    # Get module progress for marking completion
    module = LearningModule.objects.filter(
        language=language,
        proficiency_level=level
    ).first()
    
    progress = None
    if module:
        progress, _ = UserModuleProgress.objects.get_or_create(
            user=request.user,
            module=module
        )
    
    # Get flashcards and quiz questions
    flashcards = lesson.cards.all().order_by('order')
    quiz_questions = lesson.quiz_questions.all().order_by('order')
    
    context = {
        'language': language,
        'level': level,
        'skill': skill,
        'lesson': lesson,
        'flashcards': flashcards,
        'quiz_questions': quiz_questions,
        'progress': progress,
        'is_complete': progress and lesson.id in progress.lessons_completed,
    }
    
    # Choose template based on skill type
    template_name = f'curriculum/lesson_{skill}.html'
    try:
        return render(request, template_name, context)
    except TemplateDoesNotExist:
        return render(request, 'curriculum/lesson_base.html', context)


@login_required
@require_POST
def complete_curriculum_lesson(request, language, level, skill):
    """
    Mark a curriculum lesson as complete and award XP.
    
    Args:
        request: HTTP request object
        language: Target language
        level: Proficiency level
        skill: Skill category
    
    Returns:
        JsonResponse: Success/failure response
    """
    from .models import LearningModule, UserModuleProgress, SkillCategory
    
    language = language.strip().title()
    skill = skill.strip().lower()
    
    # Get the lesson
    skill_category = get_object_or_404(SkillCategory, name=skill)
    lesson = get_object_or_404(
        Lesson,
        language=language,
        difficulty_level=level,
        skill_category=skill_category,
        is_published=True
    )
    
    # Get module progress
    module = get_object_or_404(
        LearningModule,
        language=language,
        proficiency_level=level
    )
    
    progress, _ = UserModuleProgress.objects.get_or_create(
        user=request.user,
        module=module
    )
    
    # Mark lesson complete
    if lesson.id not in progress.lessons_completed:
        progress.mark_lesson_complete(lesson.id)
        
        # Award XP
        if hasattr(request.user, 'profile'):
            xp_result = request.user.profile.award_xp(lesson.xp_value)
        else:
            xp_result = {'xp_awarded': 0}
        
        # Record lesson completion
        LessonCompletion.objects.create(
            user=request.user,
            lesson_id=str(lesson.id),
            lesson_title=lesson.title,
            language=language,
            duration_minutes=5  # Estimated
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Lesson completed! +{xp_result.get("xp_awarded", 0)} XP',
            'lessons_completed': len(progress.lessons_completed),
            'can_take_test': progress.all_lessons_completed(),
        })
    
    return JsonResponse({
        'success': True,
        'message': 'Lesson already completed',
        'lessons_completed': len(progress.lessons_completed),
        'can_take_test': progress.all_lessons_completed(),
    })


@login_required
def module_test_generate(request, language, level):
    """
    Generate the adaptive test asynchronously (called from loading page).
    
    Args:
        request: HTTP request object
        language: Target language
        level: Proficiency level
    
    Returns:
        JsonResponse: Success/error status
    """
    import json
    from django.http import JsonResponse
    from .models import LearningModule
    
    language = language.strip().title()
    
    # Get the module
    module = get_object_or_404(
        LearningModule,
        language=language,
        proficiency_level=level
    )
    
    # Check if user can take the test
    test_service = AdaptiveTestService()
    test_status = test_service.can_take_test(request.user, module)
    
    if not test_status['can_take']:
        return JsonResponse({
            'success': False,
            'error': test_status['reason']
        }, status=403)
    
    try:
        # Generate the test
        test_data = test_service.generate_adaptive_test(
            request.user, language, level
        )
        
        # Store test data in session for validation on submit
        request.session[f'test_{language}_{level}'] = test_data
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'test_id': test_data.get('test_id'),
            'total_questions': test_data.get('total_questions', 0)
        })
    except Exception as e:
        logger.error('Error generating test: %s', str(e), exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to generate test. Please try again.'
        }, status=500)


@login_required
def module_test(request, language, level):
    """
    Display the adaptive test for a module.
    
    Shows loading page if test not yet generated, otherwise displays the test.
    
    Args:
        request: HTTP request object
        language: Target language
        level: Proficiency level
    
    Returns:
        HttpResponse: Rendered test template, loading page, or redirect if not eligible
    """
    from .models import LearningModule
    
    language = language.strip().title()
    
    # Get the module
    module = get_object_or_404(
        LearningModule,
        language=language,
        proficiency_level=level
    )
    
    # Check if user can take the test
    test_service = AdaptiveTestService()
    test_status = test_service.can_take_test(request.user, module)
    
    if not test_status['can_take']:
        messages.warning(request, test_status['reason'])
        return redirect('module_detail', language=language, level=level)
    
    # Check if test is already generated in session
    session_key = f'test_{language}_{level}'
    test_data = request.session.get(session_key)
    
    # If test not generated yet, show loading page
    if not test_data:
        context = {
            'language': language,
            'level': level,
            'module': module,
        }
        return render(request, 'curriculum/test_loading.html', context)
    
    # Test is ready, display it
    context = {
        'language': language,
        'level': level,
        'module': module,
        'test': test_data,
        'questions': test_data['questions'],
        'time_limit': test_data['time_limit_minutes'],
    }
    
    return render(request, 'curriculum/test.html', context)


@login_required
@require_POST
def submit_module_test(request, language, level):
    """
    Submit and evaluate a module test.
    
    Args:
        request: HTTP request object
        language: Target language
        level: Proficiency level
    
    Returns:
        JsonResponse: Test results with score and progression info
    """
    from .models import LearningModule
    
    language = language.strip().title()
    
    # Get the module
    module = get_object_or_404(
        LearningModule,
        language=language,
        proficiency_level=level
    )
    
    # Get test data from session
    session_key = f'test_{language}_{level}'
    test_data = request.session.get(session_key)
    
    if not test_data:
        return JsonResponse({
            'error': 'Test session expired. Please start a new test.'
        }, status=400)
    
    # Parse answers from request
    try:
        data = json.loads(request.body)
        user_answers = data.get('answers', [])
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request data'}, status=400)
    
    # Grade answers
    questions = test_data['questions']
    graded_answers = []
    
    for answer in user_answers:
        q_id = answer.get('question_id')
        user_answer = answer.get('answer_index')
        
        # Find the question
        question = next((q for q in questions if q['id'] == q_id), None)
        if question:
            is_correct = user_answer == question['correct_index']
            graded_answers.append({
                'question_id': q_id,
                'is_correct': is_correct,
                'skill': question.get('skill', 'vocabulary'),
                'correct_index': question['correct_index'],
                'user_answer': user_answer,
            })
    
    # Evaluate with the service
    test_service = AdaptiveTestService()
    result = test_service.evaluate_test(request.user, module, graded_answers)
    
    # Clear test from session
    del request.session[session_key]
    
    # Return results
    return JsonResponse({
        'success': True,
        'score': result['score'],
        'correct': result['correct'],
        'total': result['total'],
        'passed': result['passed'],
        'new_level': result['new_level'],
        'feedback': result['feedback'],
        'can_retry_at': result['can_retry_at'].isoformat() if result['can_retry_at'] else None,
        'redirect_url': reverse('test_results', kwargs={
            'language': language,
            'level': level,
        }) if result['passed'] else None,
    })


@login_required
def test_results(request, language, level):
    """
    Display test results page.
    
    Args:
        request: HTTP request object
        language: Target language
        level: Proficiency level
    
    Returns:
        HttpResponse: Rendered results template
    """
    from .models import LearningModule, UserModuleProgress
    
    language = language.strip().title()
    
    module = get_object_or_404(
        LearningModule,
        language=language,
        proficiency_level=level
    )
    
    progress = UserModuleProgress.objects.filter(
        user=request.user,
        module=module
    ).first()
    
    context = {
        'language': language,
        'level': level,
        'module': module,
        'progress': progress,
        'passed': progress.is_module_complete if progress else False,
        'best_score': progress.best_test_score if progress else 0,
        'next_level': level + 1 if level < 10 else None,
    }
    
    return render(request, 'curriculum/test_results.html', context)


@login_required
@require_POST
def generate_tts(request):
    """
    API endpoint for text-to-speech generation.
    
    Args:
        request: HTTP request with JSON body {text, language}
    
    Returns:
        JsonResponse: Audio data or browser TTS configuration
    """
    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
        language = data.get('language', 'Spanish')
        
        if not text:
            return JsonResponse({'error': 'Text is required'}, status=400)
        
        tts_service = TTSService()
        result = tts_service.generate_audio(text, language)
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error('TTS generation error: %s', str(e))
        return JsonResponse({'error': 'TTS generation failed'}, status=500)
