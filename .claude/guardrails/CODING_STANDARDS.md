# Python/Django Style Guide

**Language Learning Platform - Coding Standards**

**Version**: 1.0
**Last Updated**: October 29, 2025
**Status**: Active as of Sprint 3

This document defines the coding standards for all Python and Django code in this project. All team members must follow these guidelines to ensure consistency, maintainability, and code quality.

---

## Table of Contents

1. [General Principles](#general-principles)
2. [Python Style (PEP 8)](#python-style-pep-8)
3. [Django Conventions](#django-conventions)
4. [Naming Conventions](#naming-conventions)
5. [Code Organization](#code-organization)
6. [Functions and Methods](#functions-and-methods)
7. [Documentation](#documentation)
8. [Error Handling](#error-handling)
9. [Imports](#imports)
10. [Type Hints](#type-hints)
11. [Testing Standards](#testing-standards)
12. [Database and Models](#database-and-models)
13. [Templates and Frontend](#templates-and-frontend)
14. [Security Practices](#security-practices)
15. [Performance Considerations](#performance-considerations)
16. [Code Review Checklist](#code-review-checklist)

---

## General Principles

### Core Values
1. **Readability First**: Code is read more often than written
2. **Explicit is Better Than Implicit**: Clear over clever
3. **Consistency**: Follow existing patterns in the codebase
4. **DRY (Don't Repeat Yourself)**: Extract common functionality
5. **YAGNI (You Aren't Gonna Need It)**: Don't build for hypothetical futures
6. **Separation of Concerns**: Each component should have a single responsibility

### Code Quality Standards
- **Pylint Score**: Maintain 10/10 (Sprint 4 requirement)
- **Test Coverage**: Maintain ≥90% (current: 93%)
- **All Tests Must Pass**: No commits with failing tests
- **No Warnings in Production**: Address all linter warnings before merging

### SOFA Principles (MANDATORY)

**SOFA** = **S**ingle Responsibility, **O**pen/Closed, **F**unction Extraction, **A**void Repetition

All code must follow SOFA principles. Apply these when writing new code AND when refactoring existing code.

#### 1. Single Responsibility Principle (SRP)
Each function/class should have ONE clear purpose.

```python
# ❌ BAD: View doing too much
def progress_view(request):
    # Mixing business logic with view logic!
    weekly_challenges = UserDailyQuestAttempt.objects.filter(
        user=request.user,
        is_completed=True,
        completed_at__gte=timezone.now() - timedelta(days=7)
    )
    correct = weekly_challenges.aggregate(Sum('correct_answers'))['correct_answers__sum'] or 0
    total = weekly_challenges.aggregate(Sum('total_questions'))['total_questions__sum'] or 0
    accuracy = (correct / total * 100) if total > 0 else 0
    return render(request, 'progress.html', {'accuracy': accuracy})

# ✅ GOOD: Separated concerns
def progress_view(request):
    # View only handles HTTP - business logic delegated to service
    stats = DailyQuestService.get_weekly_stats(request.user)
    return render(request, 'progress.html', {'stats': stats})

# Service layer handles business logic
class DailyQuestService:
    @staticmethod
    def get_weekly_stats(user):
        week_ago = timezone.now() - timedelta(days=7)
        challenges = UserDailyQuestAttempt.objects.filter(
            user=user,
            is_completed=True,
            completed_at__gte=week_ago
        )
        stats = challenges.aggregate(
            correct=Sum('correct_answers'),
            total=Sum('total_questions')
        )
        accuracy = DailyQuestService._calculate_accuracy(stats['correct'], stats['total'])
        return {'accuracy': accuracy}
```

#### 2. Open/Closed Principle
Open for extension, closed for modification. Use composition and inheritance.

```python
# ✅ GOOD: Extensible design
class QuestRewardCalculator:
    """Base calculator - closed for modification"""
    def calculate_reward(self, correct, total):
        raise NotImplementedError

class ProportionalRewardCalculator(QuestRewardCalculator):
    """Extension - open for extension"""
    def calculate_reward(self, correct, total):
        return int((correct / total) * 50)

class BonusRewardCalculator(QuestRewardCalculator):
    """Another extension"""
    def calculate_reward(self, correct, total):
        base = int((correct / total) * 50)
        return base * 2 if correct == total else base
```

#### 3. Function Extraction
Extract complex logic into helper functions. Keep functions focused and short.

```python
# ❌ BAD: Large function doing too much
def submit_quest(request):
    quest = get_object_or_404(DailyQuest, date=date.today())
    correct_answers = 0
    total_questions = quest.questions.count()

    # 20 lines of answer validation
    for question in quest.questions.all():
        answer = request.POST.get(f'question_{question.order}')
        if answer is not None:
            try:
                answer_index = int(answer)
                if answer_index == question.correct_index:
                    correct_answers += 1
            except (ValueError, TypeError):
                pass

    # XP calculation
    xp = int((correct_answers / total_questions) * quest.xp_reward)

    # Create attempt record
    attempt = UserDailyQuestAttempt.objects.create(...)
    request.user.profile.award_xp(xp)
    messages.success(request, f'Earned {xp} XP!')
    return redirect('daily_quest')

# ✅ GOOD: Extracted into focused functions
def submit_quest(request):
    quest = get_object_or_404(DailyQuest, date=date.today())
    score = DailyQuestService.calculate_quest_score(quest, request.POST)
    DailyQuestService.record_quest_attempt(request.user, quest, score)
    messages.success(request, f"Earned {score['xp_earned']} XP!")
    return redirect('daily_quest')
```

#### 4. Avoid Repetition (DRY)
Never copy-paste code. Extract common patterns into reusable functions.

```python
# ❌ BAD: Repeated calculation logic
def get_weekly_stats(user):
    challenges = UserDailyQuestAttempt.objects.filter(...)
    stats = challenges.aggregate(correct=Sum('correct_answers'), total=Sum('total_questions'))
    # Repeated accuracy calculation #1
    if stats['total'] and stats['total'] > 0:
        accuracy = (stats['correct'] / stats['total']) * 100
    else:
        accuracy = 0
    return {'accuracy': accuracy}

def get_lifetime_stats(user):
    challenges = UserDailyQuestAttempt.objects.filter(...)
    stats = challenges.aggregate(correct=Sum('correct_answers'), total=Sum('total_questions'))
    # Repeated accuracy calculation #2 (DUPLICATE!)
    if stats['total'] and stats['total'] > 0:
        accuracy = (stats['correct'] / stats['total']) * 100
    else:
        accuracy = 0
    return {'accuracy': accuracy}

# ✅ GOOD: Extracted helper function
@staticmethod
def _calculate_accuracy(correct, total):
    """Helper to calculate accuracy percentage (DRY principle)"""
    return (correct / total * 100) if total and total > 0 else 0

def get_weekly_stats(user):
    challenges = UserDailyQuestAttempt.objects.filter(...)
    stats = challenges.aggregate(correct=Sum('correct_answers'), total=Sum('total_questions'))
    accuracy = DailyQuestService._calculate_accuracy(stats['correct'], stats['total'])
    return {'accuracy': accuracy}

def get_lifetime_stats(user):
    challenges = UserDailyQuestAttempt.objects.filter(...)
    stats = challenges.aggregate(correct=Sum('correct_answers'), total=Sum('total_questions'))
    accuracy = DailyQuestService._calculate_accuracy(stats['correct'], stats['total'])
    return {'accuracy': accuracy}
```

#### SOFA Refactoring Checklist
Before committing code, verify:

- [ ] **Single Responsibility**: Does each function have ONE clear purpose?
- [ ] **Layer Separation**: Is business logic separated from views/presentation?
- [ ] **Function Length**: Are functions under 40 lines? (Exceptions allowed with justification)
- [ ] **No Duplication**: Is there any copy-pasted code?
- [ ] **Helper Functions**: Are complex calculations extracted?
- [ ] **Magic Numbers**: Are literal numbers replaced with named constants?
- [ ] **Extensibility**: Can this be extended without modification?

#### When to Apply SOFA
- ✅ When writing new features
- ✅ After completing implementation (refactor before committing)
- ✅ During code reviews
- ✅ When fixing bugs in existing code
- ✅ When user explicitly requests it

---

## Python Style (PEP 8)

### Line Length
```python
# Maximum line length: 120 characters
# This is more permissive than PEP 8's 79, suitable for modern displays

# BAD: Line too long
def some_function():
    logger.info(f"This is a very long message that exceeds the maximum line length and should be broken into multiple lines for readability")

# GOOD: Line broken appropriately
def some_function():
    logger.info(
        "This is a very long message that has been broken into "
        "multiple lines for better readability"
    )
```

### Indentation
```python
# Use 4 spaces per indentation level (never tabs)

# GOOD
def calculate_total(items):
    total = 0
    for item in items:
        if item.is_valid:
            total += item.price
    return total
```

### Blank Lines
```python
# Two blank lines between top-level definitions
class FirstClass:
    pass


class SecondClass:
    pass


# One blank line between method definitions
class MyClass:
    def first_method(self):
        pass

    def second_method(self):
        pass


# Use blank lines sparingly inside functions to show logical sections
def complex_function():
    # Setup
    data = fetch_data()

    # Processing
    processed = transform(data)

    # Return
    return processed
```

### Whitespace
```python
# Whitespace in expressions and statements

# GOOD
x = 1
y = 2
long_variable = 3

# BAD
x             = 1
y             = 2
long_variable = 3

# GOOD
spam(ham[1], {eggs: 2})

# BAD
spam( ham[ 1 ], { eggs: 2 } )

# GOOD
if x == 4:
    print(x, y)
    x, y = y, x

# BAD
if x == 4 :
    print(x , y)
    x , y = y , x
```

---

## Django Conventions

### Project Structure
```
project_root/
├── config/              # Project settings and main URLs
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── app_name/            # Django app
│   ├── migrations/
│   ├── templates/
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
└── manage.py
```

### Model Conventions
```python
# Models should be singular nouns
class User(models.Model):  # GOOD
class Users(models.Model):  # BAD

# Field ordering: database fields, then Meta, then methods
class UserProfile(models.Model):
    # Database fields (in logical order)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Metadata
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    # String representation
    def __str__(self):
        return f"{self.user.username}'s Profile"

    # Custom methods
    def get_full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"
```

### View Conventions
```python
# Use function-based views for simple logic
def landing_page(request):
    """Display the landing page."""
    return render(request, 'landing.html')

# Use class-based views for CRUD operations
from django.views.generic import ListView, DetailView

class ArticleListView(ListView):
    """Display list of published articles."""
    model = Article
    template_name = 'articles/list.html'
    context_object_name = 'articles'
    paginate_by = 20

    def get_queryset(self):
        return Article.objects.filter(published=True).order_by('-created_at')
```

### URL Patterns
```python
# Use descriptive URL names for reverse lookups
urlpatterns = [
    path('', views.landing, name='landing'),  # GOOD
    path('', views.landing, name='view1'),     # BAD

    # Use path() over re_path() when possible
    path('articles/<int:pk>/', views.article_detail, name='article_detail'),  # GOOD
    re_path(r'^articles/(?P<pk>\d+)/$', views.article_detail),                # BAD

    # Group related URLs
    path('account/', views.account_view, name='account'),
    path('account/settings/', views.account_settings, name='account_settings'),
    path('account/delete/', views.account_delete, name='account_delete'),
]
```

---

## Naming Conventions

### General Rules
```python
# Variables and functions: lowercase_with_underscores
user_count = 10
def get_user_profile():
    pass

# Classes: CapitalizedWords (PascalCase)
class UserProfile:
    pass

# Constants: UPPERCASE_WITH_UNDERSCORES
MAX_LOGIN_ATTEMPTS = 5
DEFAULT_TIMEOUT = 300

# "Private" (internal): single leading underscore
def _internal_helper():
    pass

_internal_variable = "hidden"

# Name mangling (rarely used): double leading underscore
class MyClass:
    def __private_method(self):
        pass
```

### Django-Specific Naming
```python
# Model fields: descriptive, lowercase_with_underscores
class Article:
    created_at = models.DateTimeField(auto_now_add=True)  # GOOD
    created = models.DateTimeField(auto_now_add=True)      # OK but less clear
    dt = models.DateTimeField(auto_now_add=True)           # BAD

# Related names: plural for reverse relations
class Comment(models.Model):
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name='comments'  # article.comments.all()
    )

# View function names: verb_noun or noun_verb pattern
def list_articles(request):      # GOOD
def article_list(request):       # GOOD
def articles(request):           # Less clear
def view1(request):              # BAD

# URL names: noun_verb or app_noun_verb
name='article_list'              # GOOD
name='list_articles'             # GOOD
name='articles'                  # Less clear
```

### Boolean Variables
```python
# Use is_, has_, can_, should_ prefixes for booleans
is_active = True
has_permission = False
can_edit = True
should_retry = False

# BAD
active = True      # Ambiguous
permission = False # What does False mean?
```

---

## Code Organization

### File Organization
```python
"""
Module docstring explaining the purpose of this file.

This module handles user authentication and session management.
"""

# Standard library imports
import logging
import time
from datetime import datetime, timedelta

# Third-party imports
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

# Local application imports
from .models import UserProfile, LoginAttempt
from .forms import LoginForm, SignupForm

# Constants
MAX_LOGIN_ATTEMPTS = 5
LOGIN_TIMEOUT = 300

# Module-level variables (if necessary)
logger = logging.getLogger(__name__)

# Functions and classes (in logical order)
```

### Import Ordering
```python
# 1. Standard library
import os
import sys
from datetime import datetime

# 2. Third-party packages
import django
from django.db import models
from rest_framework import serializers

# 3. Local application/library specific
from .models import User
from ..utils import helper_function

# Within each group, imports should be alphabetical
```

---

## Functions and Methods

### Single Return Statement Principle
```python
# GOOD: Single return point (when practical)
def calculate_discount(price, user):
    """Calculate discount for user purchase."""
    # Guard clauses for validation (early returns OK)
    if price <= 0:
        return 0
    if not user.is_authenticated:
        return 0

    # Main logic with single return
    discount = 0
    if user.is_premium:
        discount = price * 0.20
    elif user.has_membership:
        discount = price * 0.10

    return discount

# ACCEPTABLE: Multiple returns for validation/error cases
def process_payment(amount, user):
    """Process payment for user."""
    # Early returns for error conditions
    if amount <= 0:
        return None, "Invalid amount"

    if not user.has_payment_method:
        return None, "No payment method"

    # Main logic
    result = charge_payment(amount, user)
    return result, "Success"
```

### Function Length
```python
# Keep functions focused and concise (generally <50 lines)
# If longer, consider breaking into smaller functions

# BAD: Too long, does too many things
def process_order(order):
    # 100+ lines of mixed validation, processing, email, logging...
    pass

# GOOD: Broken into logical pieces
def process_order(order):
    """Process customer order."""
    if not _validate_order(order):
        return False

    _update_inventory(order)
    _charge_customer(order)
    _send_confirmation_email(order)
    _log_order_completion(order)

    return True

def _validate_order(order):
    """Validate order has required fields."""
    return order.items and order.customer

def _update_inventory(order):
    """Update inventory for order items."""
    for item in order.items:
        item.product.decrease_stock(item.quantity)
```

### Function Arguments
```python
# Limit function arguments (≤5 is ideal, ≤7 maximum)

# BAD: Too many arguments
def create_user(username, email, password, first_name, last_name,
                phone, address, city, state, zip_code):
    pass

# GOOD: Group related data into objects/dicts
def create_user(username, email, password, profile_data):
    """
    Create new user account.

    Args:
        username: Unique username
        email: User email address
        password: Raw password (will be hashed)
        profile_data: Dict with keys: first_name, last_name, phone, address
    """
    pass

# Or use a dataclass/NamedTuple for structured data
from dataclasses import dataclass

@dataclass
class UserProfile:
    first_name: str
    last_name: str
    phone: str
    address: str

def create_user(username, email, password, profile: UserProfile):
    pass
```

### Default Arguments
```python
# Never use mutable default arguments

# BAD
def add_item(item, items=[]):
    items.append(item)
    return items

# GOOD
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

---

## Documentation

### Docstrings
```python
# All modules, classes, and public functions must have docstrings

# Module docstring
"""
User authentication and authorization module.

This module provides functionality for user login, logout, password reset,
and permission checking.
"""

# Function docstring (Google style)
def calculate_total(items, tax_rate=0.08, discount=0):
    """
    Calculate order total with tax and discount.

    Args:
        items: List of OrderItem objects
        tax_rate: Tax rate as decimal (default: 0.08 for 8%)
        discount: Discount amount to subtract from subtotal

    Returns:
        Decimal: Final total amount after tax and discount

    Raises:
        ValueError: If items list is empty or tax_rate is negative

    Example:
        >>> items = [OrderItem(price=10), OrderItem(price=20)]
        >>> calculate_total(items, tax_rate=0.08)
        Decimal('32.40')
    """
    if not items:
        raise ValueError("Items list cannot be empty")
    if tax_rate < 0:
        raise ValueError("Tax rate cannot be negative")

    subtotal = sum(item.price for item in items)
    subtotal -= discount
    total = subtotal * (1 + tax_rate)

    return total

# Class docstring
class UserProfile(models.Model):
    """
    Extended user profile information.

    Stores additional user data beyond Django's default User model,
    including preferences, statistics, and metadata.

    Attributes:
        user: OneToOne link to Django User model
        bio: User biography text (optional)
        avatar: Profile picture (optional)
        created_at: Timestamp of profile creation
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    # ...
```

### Code Comments
```python
# Use comments to explain WHY, not WHAT

# BAD: Comment states the obvious
# Increment counter by 1
counter += 1

# GOOD: Comment explains reasoning
# Add 1 to account for zero-indexing in display
counter += 1

# BAD: Redundant comment
# Get user by ID
user = User.objects.get(id=user_id)

# GOOD: Explains business logic
# Only active users can access premium features
if user.is_active and user.has_subscription:
    grant_access()

# Use TODO comments for future improvements
# TODO(username): Add pagination when user count exceeds 1000
users = User.objects.all()

# Use FIXME for known issues
# FIXME(username): Race condition possible here, needs locking
update_counter()
```

### Django Model Documentation
```python
class Article(models.Model):
    """
    Blog article model.

    Represents a published or draft blog article with metadata,
    content, and relationships to authors and categories.
    """
    title = models.CharField(
        max_length=200,
        help_text="Article title (shown in list and detail views)"
    )
    slug = models.SlugField(
        unique=True,
        help_text="URL-friendly version of title"
    )
    content = models.TextField(
        help_text="Main article content (Markdown supported)"
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Publication timestamp (null = draft)"
    )

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'Article'
        verbose_name_plural = 'Articles'

    def __str__(self):
        return self.title

    def is_published(self):
        """Check if article is published (has publication date)."""
        return self.published_at is not None
```

---

## Error Handling

### Exceptions
```python
# Use specific exceptions, not bare except

# BAD
try:
    user = User.objects.get(id=user_id)
except:
    return None

# GOOD
try:
    user = User.objects.get(id=user_id)
except User.DoesNotExist:
    logger.warning("User not found: %s", user_id)
    return None

# Catch multiple specific exceptions
try:
    result = process_payment(amount)
except (PaymentError, NetworkError) as e:
    logger.error("Payment failed: %s", str(e))
    return False

# Use broad exceptions only when necessary, with justification
try:
    plugin.execute()
except Exception as e:  # pylint: disable=broad-exception-caught
    # Catch all to prevent plugin failures from crashing app
    logger.error("Plugin execution failed: %s", type(e).__name__)
```

### Error Messages
```python
# Error messages should be clear and actionable

# BAD
raise ValueError("Invalid input")

# GOOD
raise ValueError(
    f"Invalid email format: '{email}'. "
    "Email must contain '@' and a domain."
)

# For user-facing errors, don't expose internal details
# BAD (security issue)
return JsonResponse({
    'error': f'Database error: {str(e)}'
})

# GOOD
logger.error("Database error processing request: %s", str(e))
return JsonResponse({
    'error': 'An error occurred. Please try again later.'
})
```

### Validation
```python
# Validate early, fail fast

def create_order(items, customer):
    """Create new order for customer."""
    # Validation at the top
    if not items:
        raise ValueError("Order must contain at least one item")
    if not customer.is_active:
        raise ValueError("Customer account is not active")
    if not customer.has_payment_method:
        raise ValueError("Customer has no payment method on file")

    # Main logic after validation
    order = Order.objects.create(customer=customer)
    for item in items:
        order.add_item(item)

    return order
```

---

## Imports

### Order and Organization
```python
# Group imports in this order:
# 1. Standard library
# 2. Third-party packages
# 3. Local application

# Within each group, alphabetize by module name

# GOOD
import logging
import os
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.shortcuts import render, redirect

from .forms import LoginForm
from .models import User, UserProfile

# BAD - mixed ordering
from .models import User
import os
from django.contrib.auth import authenticate
import logging
```

### Import Styles
```python
# Prefer importing modules, not names

# GOOD
from django.contrib import auth
user = auth.authenticate(username=username, password=password)

# ACCEPTABLE
from django.contrib.auth import authenticate
user = authenticate(username=username, password=password)

# Avoid wildcard imports
# BAD
from django.contrib.auth import *

# Avoid relative imports that go up multiple levels
# BAD
from ....utils import helper

# GOOD
from app_name.utils import helper
```

---

## Type Hints

### Usage
```python
# Use type hints for function signatures (Python 3.9+)

from typing import List, Dict, Optional, Union
from decimal import Decimal

def calculate_total(
    items: List[Dict[str, Union[str, Decimal]]],
    tax_rate: float = 0.08,
    discount: Decimal = Decimal('0')
) -> Decimal:
    """Calculate order total with tax and discount."""
    pass

# Use Optional for values that can be None
def get_user(user_id: int) -> Optional[User]:
    """Retrieve user by ID, returns None if not found."""
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None

# Django model return types
def get_recent_articles(limit: int = 10) -> QuerySet[Article]:
    """Get recent published articles."""
    return Article.objects.filter(
        published=True
    ).order_by('-created_at')[:limit]
```

---

## Testing Standards

See also: **CLAUDE.md** for comprehensive testing guidance.

### Test Organization
```python
# Organize tests by feature/model
class UserModelTests(TestCase):
    """Tests for User model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_user_creation(self):
        """Test user is created with correct attributes."""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(self.user.check_password('testpass123'))

    def test_user_str_representation(self):
        """Test string representation of user."""
        self.assertEqual(str(self.user), 'testuser')
```

### Test Naming
```python
# Test names should describe what they test

# GOOD
def test_login_with_invalid_password_fails(self):
def test_user_can_update_email_address(self):
def test_calculate_discount_for_premium_user(self):

# BAD
def test_login(self):
def test_user(self):
def test_1(self):
```

### Test Independence
```python
# Each test must be completely independent

# BAD
class BadTestClass(TestCase):
    def test_create_user(self):
        self.user = User.objects.create(username='test')

    def test_update_user(self):
        # Depends on test_create_user running first!
        self.user.email = 'new@example.com'
        self.user.save()

# GOOD
class GoodTestClass(TestCase):
    def setUp(self):
        """Create fresh test data for each test."""
        self.user = User.objects.create(username='test')

    def test_create_user(self):
        user = User.objects.create(username='test2')
        self.assertEqual(user.username, 'test2')

    def test_update_user(self):
        self.user.email = 'new@example.com'
        self.user.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'new@example.com')
```

### Mocking
```python
# Mock external dependencies to prevent flaky tests

from unittest.mock import patch, MagicMock

class EmailTestCase(TestCase):
    @patch('home.views.send_mail')
    def test_password_reset_sends_email(self, mock_send_mail):
        """Test password reset sends email to user."""
        mock_send_mail.return_value = 1

        response = self.client.post('/forgot-password/', {
            'email': 'test@example.com'
        })

        self.assertEqual(response.status_code, 200)
        mock_send_mail.assert_called_once()
```

---

## Database and Models

### Query Optimization
```python
# Use select_related for foreign keys (one-to-one, many-to-one)
articles = Article.objects.select_related('author').all()

# Use prefetch_related for reverse foreign keys (one-to-many, many-to-many)
users = User.objects.prefetch_related('articles').all()

# Combine for complex queries
articles = Article.objects.select_related(
    'author'
).prefetch_related(
    'comments',
    'tags'
).all()

# Use only() or defer() to limit fields
users = User.objects.only('username', 'email').all()
```

### Model Methods
```python
# Put business logic in model methods, not views

# GOOD
class Order(models.Model):
    def calculate_total(self):
        """Calculate order total including tax."""
        subtotal = sum(item.price for item in self.items.all())
        tax = subtotal * self.tax_rate
        return subtotal + tax

# In view
order = Order.objects.get(id=order_id)
total = order.calculate_total()

# BAD - logic in view
order = Order.objects.get(id=order_id)
items = order.items.all()
subtotal = sum(item.price for item in items)
tax = subtotal * order.tax_rate
total = subtotal + tax
```

---

## Templates and Frontend

### Template Organization
```python
# Use template inheritance
# base.html
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}My Site{% endblock %}</title>
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>

# article_detail.html
{% extends 'base.html' %}

{% block title %}{{ article.title }} - My Site{% endblock %}

{% block content %}
    <h1>{{ article.title }}</h1>
    <p>{{ article.content }}</p>
{% endblock %}
```

### Template Logic
```python
# Keep logic in views, not templates

# BAD - complex logic in template
{% for article in articles %}
    {% if article.published and article.author.is_active and article.category != 'draft' %}
        ...
    {% endif %}
{% endfor %}

# GOOD - filter in view
def article_list(request):
    articles = Article.objects.filter(
        published=True,
        author__is_active=True
    ).exclude(category='draft')
    return render(request, 'articles.html', {'articles': articles})
```

### DevEDU Environment Compatibility

**IMPORTANT**: All templates must be compatible with the DevEDU testing environment, which uses a reverse proxy at `/proxy/8000/`.

#### Required Template Structure
Templates should be standalone HTML files (not using template inheritance) with the following structure:

```django
{% load static %}
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Page Title - Language Learning Platform</title>
    {% if IS_DEVEDU %}<base href="/proxy/8000{{ request.path }}{% if not request.path|slice:'-1:' == '/' %}/{% endif %}">{% endif %}
    <link rel="stylesheet" href="{% static 'home/styles.css' %}">
  </head>
  <body>
    {% include '_nav.html' %}

    <main>
      <!-- Django Messages -->
      {% if messages %}
        <div class="page-messages">
          {% for message in messages %}
            <div class="alert alert-{{ message.tags }}">
              {{ message }}
            </div>
          {% endfor %}
        </div>
      {% endif %}

      <section class="hero">
        <div class="hero-content">
          <!-- Page content here -->
        </div>
      </section>
    </main>

    <footer>
      <p>&copy; 2025 Language Learning Platform. Start learning today!</p>
    </footer>

    <script>
      // Mobile menu toggle
      const navToggle = document.querySelector('.nav-toggle');
      const navMenu = document.querySelector('.nav-menu');

      if (navToggle) {
        navToggle.addEventListener('click', () => {
          navMenu.classList.toggle('active');
          navToggle.classList.toggle('active');
        });

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
          if (!navToggle.contains(e.target) && !navMenu.contains(e.target)) {
            navMenu.classList.remove('active');
            navToggle.classList.remove('active');
          }
        });
      }
    </script>
  </body>
</html>
```

#### Key DevEDU Requirements:
1. **Base href tag**: `{% if IS_DEVEDU %}<base href="/proxy/8000{{ request.path }}...">{% endif %}`
   - This handles the reverse proxy path in the DevEDU environment
   - Must be in the `<head>` section before any relative URLs
   - The `IS_DEVEDU` context variable is provided by `home.context_processors.devedu_context`

2. **Standalone HTML**: Templates should NOT use `{% extends %}` for inheritance
   - Use full HTML structure in each template
   - Include `{% include '_nav.html' %}` for navigation
   - Duplicate footer and scripts across templates

3. **Static files**: Always use `{% load static %}` and `{% static 'path' %}`

4. **Testing**: Verify templates work in both local and DevEDU environments

#### Context Processor Setup
Ensure `home.context_processors.devedu_context` is in `settings.TEMPLATES.OPTIONS.context_processors`:

```python
'context_processors': [
    # ... other processors
    'home.context_processors.devedu_context',
],
```

The context processor adds `IS_DEVEDU` based on the environment variable:
```python
def devedu_context(request):
    """Add IS_DEVEDU flag to template context."""
    return {
        'IS_DEVEDU': settings.IS_DEVEDU
    }
```

---

## Security Practices

See **SECURITY_GUIDE.md** for comprehensive security guidelines.

### Quick Reference
- Never commit secrets or API keys
- Use environment variables for sensitive data
- Validate all user input
- Use Django's built-in protections (CSRF, XSS, SQL injection)
- Use HTTPS in production
- Implement rate limiting for authentication endpoints
- Log security events with IP addresses
- Use generic error messages (prevent user enumeration)

---

## Performance Considerations

### Database Queries
```python
# Avoid N+1 queries
# BAD
articles = Article.objects.all()
for article in articles:
    print(article.author.name)  # Separate query for each author!

# GOOD
articles = Article.objects.select_related('author').all()
for article in articles:
    print(article.author.name)  # No extra queries
```

### Caching
```python
# Use Django's cache framework for expensive operations
from django.core.cache import cache

def get_popular_articles():
    """Get popular articles with 5-minute cache."""
    cache_key = 'popular_articles'
    articles = cache.get(cache_key)

    if articles is None:
        articles = Article.objects.filter(
            published=True
        ).order_by('-view_count')[:10]
        cache.set(cache_key, articles, 300)  # 5 minutes

    return articles
```

---

## Code Review Checklist

### Before Submitting PR
- [ ] All tests pass locally
- [ ] Pylint score 10/10
- [ ] Test coverage maintained or improved
- [ ] No commented-out code
- [ ] No debug print statements
- [ ] Docstrings added for new functions/classes
- [ ] CLAUDE.md updated if architecture changes
- [ ] Type hints added for function signatures
- [ ] Security considerations addressed
- [ ] Performance implications considered

### Reviewing Code
- [ ] Code follows this style guide
- [ ] Tests are independent and not flaky
- [ ] Error handling is appropriate
- [ ] No sensitive data in code or logs
- [ ] Database queries are optimized
- [ ] User input is validated
- [ ] Documentation is clear and complete
- [ ] Code is maintainable and readable

---

## Enforcement

### Automated Checks (Sprint 4+)
- **Pylint**: Runs on all PRs, must score 10/10
- **Tests**: All tests must pass before merge
- **Coverage**: Must maintain ≥90% coverage

### Manual Review
- All PRs require review by at least one team member
- Reviewers should reference this guide when providing feedback
- Style violations should be fixed before merge

---

## Exceptions and Special Cases

### When to Deviate
- **Legacy Code**: Gradual refactoring is acceptable
- **Third-Party Integration**: Match external API conventions when necessary
- **Performance Critical**: Document why standard approach wasn't used
- **Proof of Concepts**: Clearly mark as experimental

### How to Request Exception
1. Document reason in code comments
2. Note in PR description
3. Get team consensus if significant deviation

---

## Resources

- [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Django Coding Style](https://docs.djangoproject.com/en/stable/internals/contributing/writing-code/coding-style/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [CLAUDE.md](./CLAUDE.md) - Project-specific development guide
- [SECURITY_GUIDE.md](./SECURITY_GUIDE.md) - Security best practices

---

## Changelog

### Version 1.0 (October 29, 2025)
- Initial style guide creation
- Established baseline standards for Sprint 3
- Integrated with pylint configuration
- Added single return statement guideline
- Comprehensive testing standards

---

**Questions or Suggestions?**
Open an issue or discuss in team meetings. This guide is living document and will evolve with the project.
