# Test Suite Organization

This directory contains a well-organized test suite for the home app with **65 comprehensive tests** covering all functionality.

## Structure

```
home/tests/
├── __init__.py           # Test suite entry point
├── README.md             # This file
├── test_utils.py         # Shared test utilities and helpers
├── test_models.py        # All model tests (16 tests)
├── test_views.py         # All view tests (30 tests)
├── test_admin.py         # Admin interface tests (12 tests)
├── test_services.py      # Service layer tests (10 tests)
└── test_integration.py   # End-to-end flow tests (7 tests)
```

## Test Modules

### `test_utils.py`
Shared helpers used across all test modules:
- `create_test_user()` - Factory for creating test users
- `create_test_superuser()` - Factory for creating admin users
- `AdminTestCase` - Base class for admin tests

### `test_models.py` (16 tests)
Tests for all database models:
- **Core models**: UserProgress, LessonCompletion, QuizResult
- **Onboarding models**: UserProfile, OnboardingQuestion, OnboardingAttempt, OnboardingAnswer

Coverage: Model creation, relationships, properties, calculations, constraints

### `test_views.py` (30 tests)
Tests for all views:
- **Authentication**: Signup, login, logout (7 tests)
- **Core pages**: Landing, dashboard, progress (5 tests)
- **Account management**: Settings updates (3 tests)
- **Password recovery**: Forgot password/username (3 tests)
- **Onboarding**: Quiz flow and submission (12 tests)

Coverage: GET/POST requests, authentication requirements, form validation, redirects

### `test_admin.py` (12 tests)
Tests for Django admin interface:
- **Custom actions**: Password reset, make staff, reset progress (3 tests)
- **Access control**: Authentication and permissions (3 tests)
- **CRUD operations**: Create and edit through admin (2 tests)
- **Search/filters**: User search and filtering (4 tests)

Coverage: Admin functionality, permissions, data management

### `test_services.py` (10 tests)
Tests for service layer business logic:
- **Level calculation algorithm**: 6 comprehensive algorithm tests covering all edge cases
- **Question retrieval**: Language filtering and ordering (2 tests)
- **Weak area analysis**: Performance tracking (1 test)
- **Helper functions**: Test data creation (1 test)

Coverage: Critical onboarding algorithm, service methods

### `test_integration.py` (7 tests)
End-to-end user flow tests:
- **Authentication flows**: Signup, login, redirects (2 tests)
- **Onboarding flows**: Guest quiz → signup, quiz retake (4 tests)
- **Progress tracking**: Onboarding display on progress page (1 test)

Coverage: Complete user journeys across multiple views

## Running Tests

### Run all tests
```bash
python manage.py test home.tests
```

### Run specific module
```bash
python manage.py test home.tests.test_models
python manage.py test home.tests.test_views
python manage.py test home.tests.test_services
```

### Run specific test class
```bash
python manage.py test home.tests.test_models.UserProgressModelTest
```

### Run with coverage
```bash
pytest --cov=home --cov-report=term-missing
```

## Test Philosophy

This test suite follows these principles:

1. **Comprehensive but not redundant**: Tests cover all critical functionality without excessive duplication
2. **Organized by concern**: Tests grouped logically by what they test (models, views, etc.)
3. **Readable and maintainable**: Clear test names, good documentation, shared utilities
4. **Fast execution**: ~57 seconds for full suite, tests run independently
5. **CI/CD compatible**: Works with both Django test runner and pytest

## Coverage

The test suite provides comprehensive coverage:
- ✅ All models tested (creation, methods, properties, constraints)
- ✅ All views tested (authentication, CRUD, form handling)
- ✅ Critical algorithms tested thoroughly (onboarding level calculation)
- ✅ Admin interface tested (actions, permissions, CRUD)
- ✅ Complete user flows tested (signup → quiz → results)

## Migrating from Old Structure

The old `home/tests.py` file (2594 lines) has been reorganized into this modular structure.

**Note**: `tests.py` still exists for backward compatibility but will be deprecated. All new tests should be added to the appropriate module in `tests/`.

## Adding New Tests

When adding new tests:

1. **Choose the right module**:
   - Model logic → `test_models.py`
   - View/endpoint → `test_views.py`
   - Admin feature → `test_admin.py`
   - Service/algorithm → `test_services.py`
   - Complete user flow → `test_integration.py`

2. **Use existing utilities**:
   ```python
   from .test_utils import create_test_user, create_test_superuser
   ```

3. **Follow naming conventions**:
   - Test classes: `[Feature]Test` (e.g., `AuthenticationViewsTest`)
   - Test methods: `test_[what_is_being_tested]` (e.g., `test_signup_success`)

4. **Keep tests focused**: One test should test one thing
5. **Use descriptive docstrings**: Explain what the test validates

## Example Test

```python
class MyFeatureTest(TestCase):
    """Test my new feature"""
    
    def setUp(self):
        """Set up test data"""
        self.user = create_test_user()
    
    def test_feature_works_correctly(self):
        """Test that feature produces expected result"""
        result = my_feature(self.user)
        self.assertEqual(result.status, 'success')
```

