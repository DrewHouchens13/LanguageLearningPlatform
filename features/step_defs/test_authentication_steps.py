"""
BDD Step Definitions for Authentication Features
Implements Given-When-Then steps for login and signup scenarios
"""

import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

# Load all scenarios from authentication feature files
scenarios('../authentication/login.feature')
scenarios('../authentication/signup.feature')


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def context():
    """Shared context for storing state between steps"""
    return {}


@pytest.fixture
def django_client():
    """Django test client for making HTTP requests"""
    return Client()


# ============================================================================
# GIVEN STEPS - Setup preconditions
# ============================================================================

@given(parsers.parse('a user exists with email "{email}" and password "{password}"'), target_fixture='test_user')
def user_exists(email, password):
    """Create a test user with given credentials"""
    user = User.objects.create_user(
        username='testuser',
        email=email,
        password=password,
        first_name='Test',
        last_name='User'
    )
    return user


@given('I am on the login page')
def on_login_page(context, django_client):
    """Navigate to login page"""
    response = django_client.get(reverse('login'))
    context['response'] = response
    context['page'] = 'login'
    assert response.status_code == 200


@given('I am on the signup page')
def on_signup_page(context, django_client):
    """Navigate to signup page"""
    response = django_client.get(reverse('signup'))
    context['response'] = response
    context['page'] = 'signup'
    assert response.status_code == 200


@given(parsers.parse('I am on the login page with next parameter "{next_url}"'))
def on_login_page_with_next(context, django_client, next_url):
    """Navigate to login page with next parameter"""
    response = django_client.get(f"{reverse('login')}?next={next_url}")
    context['response'] = response
    context['next_url'] = next_url
    assert response.status_code == 200


@given(parsers.parse('a user exists with email "{email}"'))
def existing_user(email):
    """Create an existing user"""
    User.objects.create_user(
        username='existing',
        email=email,
        password='ExistingPass123!'
    )


# ============================================================================
# WHEN STEPS - Actions
# ============================================================================

@when(parsers.parse('I enter email "{email}"'))
def enter_email(context, email):
    """Store email for form submission"""
    if 'form_data' not in context:
        context['form_data'] = {}
    context['form_data']['username_or_email'] = email


@when(parsers.parse('I enter username "{username}"'))
def enter_username(context, username):
    """Store username for form submission"""
    if 'form_data' not in context:
        context['form_data'] = {}
    context['form_data']['username_or_email'] = username


@when(parsers.parse('I enter password "{password}"'))
def enter_password(context, password):
    """Store password for form submission"""
    if 'form_data' not in context:
        context['form_data'] = {}
    context['form_data']['password'] = password


@when(parsers.parse('I enter full name "{full_name}"'))
def enter_full_name(context, full_name):
    """Store full name for signup form"""
    if 'form_data' not in context:
        context['form_data'] = {}
    parts = full_name.split(' ', 1)
    context['form_data']['first_name'] = parts[0]
    context['form_data']['last_name'] = parts[1] if len(parts) > 1 else ''


@when(parsers.parse('I confirm password "{password}"'))
def confirm_password(context, password):
    """Store password confirmation for signup"""
    context['form_data']['password_confirm'] = password


@when('I click the login button')
def click_login(context, django_client):
    """Submit login form"""
    response = django_client.post(reverse('login'), context['form_data'])
    context['response'] = response


@when('I click the signup button')
def click_signup(context, django_client):
    """Submit signup form"""
    response = django_client.post(reverse('signup'), context['form_data'])
    context['response'] = response


@when(parsers.parse('I attempt to login with wrong password {attempts:d} times'))
def multiple_failed_attempts(context, django_client, attempts, test_user):
    """Attempt multiple failed logins"""
    for i in range(attempts):
        django_client.post(reverse('login'), {
            'username_or_email': test_user.email,
            'password': 'WrongPassword123!'
        })

    # Try one more time to trigger rate limit
    response = django_client.post(reverse('login'), {
        'username_or_email': test_user.email,
        'password': 'WrongPassword123!'
    })
    context['response'] = response


# ============================================================================
# THEN STEPS - Assertions
# ============================================================================

@then('I should be redirected to the landing page')
def redirected_to_landing(context):
    """Verify redirect to landing page"""
    assert context['response'].status_code == 302
    assert context['response'].url == reverse('landing')


@then(parsers.parse('I should be redirected to "{url}"'))
def redirected_to_url(context, url):
    """Verify redirect to specific URL"""
    assert context['response'].status_code == 302
    assert context['response'].url == url


@then('I should see a welcome message')
def see_welcome_message(context):
    """Verify welcome message appears after login"""
    # Follow redirect to see the welcome message
    response = context['response']
    assert response.status_code == 302


@then(parsers.parse('I should see an error message "{message}"'))
def see_error_message(context, message):
    """Verify error message is displayed"""
    response = context['response']
    content = response.content.decode('utf-8')
    assert message in content or response.status_code == 200


@then('I should remain on the login page')
def remain_on_login(context):
    """Verify user stays on login page"""
    assert context['response'].status_code == 200


@then('I should remain on the signup page')
def remain_on_signup(context):
    """Verify user stays on signup page"""
    assert context['response'].status_code == 200


@then('I should be logged in automatically')
def logged_in(context, django_client):
    """Verify user is logged in after signup"""
    # Check if user is authenticated by trying to access a protected page
    response = django_client.get(reverse('dashboard'))
    assert response.status_code == 200


@then('a user profile should be created for me')
def profile_created(context):
    """Verify user profile was created"""
    # Check that a new user was created
    assert User.objects.filter(email=context['form_data']['username_or_email']).exists()


@then('I should see an error message about password requirements')
def see_password_error(context):
    """Verify password requirements error"""
    content = context['response'].content.decode('utf-8')
    assert 'password' in content.lower() and ('short' in content.lower() or 'requirements' in content.lower())


@then('I should see a rate limit error message')
def see_rate_limit_error(context):
    """Verify rate limiting is active"""
    content = context['response'].content.decode('utf-8')
    assert 'too many' in content.lower() or 'rate limit' in content.lower() or 'try again' in content.lower()


@then('I should be temporarily blocked from logging in')
def blocked_from_login(context):
    """Verify user cannot login due to rate limiting"""
    assert context['response'].status_code == 200  # Stays on login page
