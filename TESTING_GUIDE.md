# Testing Guide

Comprehensive testing documentation for the Language Learning Platform.

## Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run specific test
pytest home/tests.py::TestClassName::test_method_name
```

## Testing Workflow

**REQUIRED WORKFLOW**: When making code changes, follow this exact order:

1. **Write/modify code** - Implement features or fixes
2. **Run Pylint** - Check code quality on ALL project files
   ```bash
   pylint home/ config/ --rcfile=.pylintrc
   ```
   - Target: 9.5+/10 score (current: 9.71-10.00/10)
   - Fix any critical issues before proceeding
   - Runs on entire home/ and config/ directories, not just modified files

3. **Run Bandit** - Security scan on ALL project files
   ```bash
   bandit -r home/ config/ -f txt
   ```
   - Target: 0 high/critical security issues
   - Address any security warnings before proceeding
   - Runs on entire home/ and config/ directories, not just modified files

4. **Run Semgrep** - Advanced CWE/OWASP security scan (GitHub workflow test)
   ```bash
   semgrep --config=p/security-audit --config=p/django --config=p/python home/ config/
   ```
   - Target: 0 high/critical findings
   - Scans for CWE patterns, OWASP vulnerabilities, Django-specific issues
   - **BLOCKING REQUIREMENT**: This runs in GitHub workflows and WILL PREVENT PR MERGE if it fails

5. **Run pip-audit** - CVE vulnerability scan for dependencies (GitHub workflow test)
   ```bash
   pip-audit -r requirements.txt --desc
   ```
   - Target: 0 known CVE vulnerabilities
   - Checks all dependencies for known security vulnerabilities
   - **BLOCKING REQUIREMENT**: This runs in GitHub workflows and WILL PREVENT PR MERGE if it fails

6. **Run Safety** - Additional dependency security check (GitHub workflow test)
   ```bash
   safety check --continue-on-error
   ```
   - Target: 0 known security vulnerabilities
   - Secondary CVE check for Python dependencies
   - **BLOCKING REQUIREMENT**: This runs in GitHub workflows and WILL PREVENT PR MERGE if it fails
   - Note: Using `--continue-on-error` to avoid authentication prompts in CI

7. **Fix linting/security issues** - Address any problems found in steps 2-6

8. **Run full test suite** - Verify all tests pass
   ```bash
   pytest
   ```

9. **Check coverage** - Ensure coverage remains high
   ```bash
   pytest --cov=home --cov=config --cov-report=term-missing
   ```
   - Target: 90%+ coverage
   - Only measures coverage for home/ and config/ apps (excludes local test files)

10. **Live testing** - Run local server and run all live testing

11. **Commit & push** - Once everything passes

This workflow ensures code quality and security issues are caught before running the test suite, making development more efficient.

## Test Categories

**Current Status**: 167 tests, 90% code coverage

**Test Distribution**:
- Model tests (20 tests)
- Authentication tests (39 tests including validation, rate limiting, redirect protection)
- Account management tests (21 tests including edge cases)
- Password recovery tests (14 tests)
- Admin tests (36 tests)
- Security tests (XSS, SQL injection, unauthorized access, input validation, user enumeration)
- Rate limiting tests (brute force prevention)
- Open redirect protection tests

## Test Quality Requirements

### Test Independence

Every test must be completely independent:

- Tests should pass when run individually or in any order
- Use `setUp()` and `tearDown()` methods or pytest fixtures to ensure clean state
- Clear cache between tests (`cache.clear()`) to prevent state leakage
- Create fresh test data for each test, never rely on data from previous tests
- Avoid global state or shared mutable objects
- Run tests in random order to detect dependencies: `pytest --random-order`

### Preventing Flaky Tests

Tests must be deterministic and reliable:

**Mock external dependencies**: Use `unittest.mock` or `pytest-mock` for:
- Network calls (APIs, external services)
- Email sending (SMTP)
- File system operations (when testing logic, not I/O)
- Time-dependent behavior (`datetime.now()`, `timezone.now()`)
- Random number generation

**Best practices**:
- **Use freezegun** for time-dependent tests: `@freeze_time('2025-01-15')`
- **Avoid sleep()**: Never use `time.sleep()` in tests; use mocks or timeouts
- **Fix random seeds**: If using random data, set seed: `random.seed(42)`
- **Mock third-party services**: Don't make real HTTP requests in tests
- **Database state**: Use Django's TestCase for automatic transaction rollback
- **Clean up resources**: Close files, connections, temp directories in tearDown

## Testing Commands

### Basic Testing

```bash
# Run all tests with pytest
pytest

# Run Django tests
python manage.py test

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run specific test
pytest home/tests.py::TestClassName::test_method_name
```

### Test Independence Verification

```bash
# Run tests in random order (pytest-random-order included in requirements.txt)
pytest --random-order

# Stop on first failure to debug test dependencies
pytest -x
```

### Mocking Tools

```bash
# Mocking tools (pytest-mock included in requirements.txt)
# Use unittest.mock.patch to mock external dependencies
# Example:
# from unittest.mock import patch, MagicMock
# @patch('home.views.send_mail')
# def test_email_sending(mock_send_mail):
#     mock_send_mail.return_value = 1
#     # Test code that calls send_mail
```

### Time Mocking

```bash
# Time mocking for deterministic tests (freezegun included in requirements.txt)
# from freezegun import freeze_time
# @freeze_time('2025-01-15 12:00:00')
# def test_time_dependent_feature():
#     # Test with fixed time
```

## Advanced Testing Techniques

### Mutation Testing

Use `mutmut` to verify test quality by introducing small code changes (mutations) and ensuring tests catch them. This validates that tests actually detect bugs, not just provide coverage.

```bash
# Run mutation tests
mutmut run

# View mutation test results
mutmut results

# Show specific mutation
mutmut show <mutation_id>

# Generate HTML report
mutmut html
```

**When to use mutation testing**:
- Run on critical security code (authentication, input validation, permissions)
- Aim for high mutation score (>80%) on security-sensitive modules
- Use to find weak tests that don't actually verify behavior

### Fuzz Testing

Use `hypothesis` to generate random test inputs and discover edge cases.

```bash
# Fuzz testing (hypothesis included in requirements.txt)
# Add @given decorators to test functions in home/tests.py
# Example:
# from hypothesis import given
# from hypothesis.strategies import text, integers
# @given(text(), integers())
# def test_with_random_inputs(string_input, int_input):
#     # Test with randomly generated inputs
```

**When to use fuzz testing**:
- Apply to input validation functions (login, signup, account updates)
- Use for data parsing and serialization functions
- Particularly valuable for security-critical code paths
- Define strategies that match your domain (email formats, usernames, passwords)
- Run fuzz tests in CI to catch unexpected edge cases

### Critical/Security Code Testing

**For Critical/Security Code (authentication, input validation, permissions)**:

1. Run mutation testing: `mutmut run` to verify tests catch actual bugs
2. Add fuzz testing with `hypothesis` to discover edge cases with random inputs
3. Review mutation survivors and add tests to catch them
4. Ensure mutation score >80% for security-critical modules

## Code Linting (Pylint)

```bash
# Pylint is included in requirements.txt

# STANDARD WORKFLOW: Run on entire project (home and config apps)
# This is what you should run during the testing workflow
pylint home/ config/ --rcfile=.pylintrc

# Run on entire app (alternative)
pylint home/

# Run with specific score threshold
pylint home/ --fail-under=8.0

# Generate configuration file (creates .pylintrc)
pylint --generate-rcfile > .pylintrc

# Run with custom config
pylint home/ --rcfile=.pylintrc

# Show only errors (ignore warnings)
pylint home/ --errors-only

# Disable specific warnings
pylint home/ --disable=C0111,C0103

# Generate report
pylint home/ --output-format=text > pylint_report.txt
```

**Note**: Pylint is integrated into the development workflow. Target score: 9.5+/10.

## Working with Tests

### Django Testing Basics

- Pytest is primary test runner (see pytest.ini)
- Django's `manage.py test` also works
- Always run tests after changes: `pytest`
- Check coverage: `pytest --cov=.`
- Write tests for edge cases and error handling
- Use Django's TestCase for database-dependent tests
- Use fixtures for common test data

### Test Configuration

**Test Requirements**:
- Uses pytest (configured in pytest.ini and conftest.py)
- Coverage reporting via pytest-cov
- `conftest.py` disables APPEND_SLASH for tests

## Common Testing Patterns

### Testing New Features

1. Write tests in `home/tests.py`
2. Use Django's TestCase for database-dependent tests
3. Run migrations if models changed: `python manage.py makemigrations && python manage.py migrate`
4. Run tests: `pytest`
5. Check coverage: `pytest --cov=.`
6. Verify test independence: `pytest --random-order`

### Testing Bug Fixes

1. Reproduce the bug (check tests or manual verification)
2. Write a test that fails (demonstrates the bug)
3. Fix the issue
4. Ensure test is independent (doesn't rely on other tests)
5. Mock external dependencies to prevent flakiness
6. Test should fail before the fix and pass after
7. Verify fix with full test suite: `pytest`
8. Run tests in random order to verify independence: `pytest --random-order`

## CI/CD Integration

**GitHub Actions Workflows**:
- `.github/workflows/coverage.yml` - Runs pytest with coverage on all pushes/PRs, posts coverage comment to PRs
- `.github/workflows/ai-code-review.yml` - OpenAI code review on PRs when Python/HTML/JS/MD files change

## Error Handling

If you encounter test errors:

1. **Test failures**: Read the full traceback, identify the failing assertion, fix root cause
2. **Import errors**: Check requirements.txt, verify file structure, check Python path
3. **Database errors**: Check DATABASE_URL, verify migrations ran, check model definitions

## Test Examples

### Example: Testing a View

```python
from django.test import TestCase, Client
from django.contrib.auth.models import User

class TestLoginView(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_login_success(self):
        response = self.client.post('/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/landing/')
```

### Example: Testing with Mocks

```python
from unittest.mock import patch
from django.test import TestCase

class TestEmailSending(TestCase):
    @patch('home.views.send_mail')
    def test_password_reset_email(self, mock_send_mail):
        mock_send_mail.return_value = 1
        # Test code that calls send_mail
        # Verify mock was called with expected arguments
        mock_send_mail.assert_called_once()
```

### Example: Testing with Time Mocking

```python
from freezegun import freeze_time
from django.test import TestCase

class TestTimeDependent(TestCase):
    @freeze_time('2025-01-15 12:00:00')
    def test_weekly_stats(self):
        # Test with fixed time
        # Time is frozen to 2025-01-15 12:00:00
        pass
```

## Best Practices Summary

1. **Always run tests after code changes**
2. **Maintain 90%+ code coverage**
3. **Write independent tests** - no dependencies between tests
4. **Mock external dependencies** - prevent flaky tests
5. **Use mutation testing** for critical security code
6. **Use fuzz testing** for input validation
7. **Run tests in random order** to detect dependencies
8. **Follow the required workflow** - Pylint → Bandit → Tests → Commit

---

**Last Updated**: 3 November 2025
**Maintained By**: Development Team
