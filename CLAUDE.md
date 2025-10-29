# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Language Learning Platform - Django 5.2.7 web application for tracking language learning progress with user authentication and progress analytics.

**Tech Stack**: Django 5.2.7, PostgreSQL (production) / SQLite (development), WhiteNoise, Gunicorn, Pytest

## Architecture

**Project Structure**:
- `config/` - Django project settings, main URL configuration, media file serving
- `home/` - Main app: authentication, progress tracking, landing pages, user profiles
- `home/models.py` - Core models: `UserProfile`, `UserProgress`, `LessonCompletion`, `QuizResult`
- `home/forms.py` - Form validation: avatar uploads, account updates
- `home/templates/` - HTML templates (index, login, progress, dashboard, account)
- `home/static/home/` - CSS stylesheets, JavaScript files
- `media/avatars/` - User-uploaded avatar images
- `config/settings.py` - Environment-aware settings (DEBUG mode, DB switching, WhiteNoise config, media files)

**Database Switching Logic** (config/settings.py:98-116):
- Production: PostgreSQL via `DATABASE_URL` environment variable
- Development: SQLite (`db.sqlite3`)
- Tests: Automatically use DEBUG=True and simplified static storage

**Authentication Flow**:
- Flexible login (accepts username or email, authenticates by username)
- Username auto-generated from email prefix during signup, deduplicated with numbers
- Views: `login_view`, `signup_view`, `logout_view` in home/views.py
- Redirects: LOGIN_REDIRECT_URL and LOGOUT_REDIRECT_URL set to 'landing'

**Progress Tracking** (home/models.py):
- `UserProgress.get_weekly_stats()` - Calculates weekly minutes, lessons, quiz accuracy
- `UserProgress.calculate_quiz_accuracy()` - Overall accuracy from all quiz results
- `progress_view` shows real data for authenticated users, CTA for guests

**URL Patterns** (home/urls.py):
- `/` - Landing page
- `/login/` - Login/signup (same template, different POST handlers)
- `/progress/` - Progress dashboard (public, shows CTA for guests)
- `/dashboard/` - Protected view (@login_required)
- `/account/` - Account management (@login_required)
- `/forgot-password/` - Password reset request
- `/reset-password/<uidb64>/<token>/` - Password reset with token
- `/forgot-username/` - Username reminder request
- `/admin/` - Django admin interface (superuser only)

**Admin Interface** (home/admin.py, home/templates/admin/base_site.html):
- Custom User admin with bulk actions: reset passwords, make/remove admins, reset progress
- **UserProfile Inline**: Avatar management embedded in User admin interface
- **Unified Navigation**: Admin panel uses same purple gradient navigation as main site
- **Staff-Only Admin Button**: Admin link appears in navigation only for staff users
- **Custom Logout**: Admin logout redirects properly in proxy environments
- Enhanced UserProgress, LessonCompletion, and QuizResult admin
- Progress information displayed in User detail view
- Full search and filter capabilities for all models

**Account Management** (home/views.py:287-572):
- `account_view` - User account settings page (@login_required)
- Update email address (requires current password verification)
- Update name (first and last)
- Update username (with uniqueness validation)
- Change password (with strength validation and session re-authentication)
- Upload custom avatar (PNG/JPG, 5MB max, auto-resized to 200x200px)
- All changes logged with IP addresses

**User Profile & Avatar System** (home/models.py, home/forms.py):
- `UserProfile` model with one-to-one relationship to User
- Automatic profile creation via Django signals when user is created
- Avatar upload with ImageField (stored in media/avatars/user_{id}/)
- Gravatar fallback using MD5 email hash (Gravatar API requirement)
  - MD5 used with `usedforsecurity=False` flag for non-cryptographic purposes
- Automatic image processing: resize to 200x200px, RGBA to RGB conversion for JPEG compatibility
- Form validation: PNG/JPG only, 5MB maximum file size
- Avatar display sizes: 32px (navigation), 80px (account), 120px (progress), 200px (dashboard)
- Avatar updates logged with IP addresses

**Password Recovery** (home/views.py:392-572):
- `forgot_password_view` - Request password reset (displays simulated email for college project)
- `reset_password_view` - Reset password with secure token (20-min expiration)
- `forgot_username_view` - Request username reminder (displays simulated email for college project)
- Token-based password reset with expiration (configurable via PASSWORD_RESET_TIMEOUT)
- Generic success messages to prevent user enumeration
- Email templates in home/templates/emails/
- **Simulated Email Display**: Instead of sending real SMTP emails (Render doesn't provide SMTP for college projects), emails are rendered and displayed in styled boxes on the page
  - Password reset and username recovery emails shown in visually distinct gradient boxes
  - Maintains demonstration value without requiring SMTP configuration
  - Preserves security features (doesn't reveal if user exists)

**Security Features** (home/views.py):
- **IP Address Validation**: Format validation using Python's ipaddress module to prevent injection attacks (home/views.py:39-87)
- **Login Attempt Logging**: All authentication events logged with validated IP addresses for security monitoring
- **Open Redirect Prevention**: Login redirects validated with `url_has_allowed_host_and_scheme()`
- **Password Validation**: Django's built-in validators (min 8 chars, not common, not numeric only)
- **Email Validation**: Format validation before account creation
- **Secure Password Reset**: Token expires after 20 minutes; admin generates 12-char random passwords
- **Generic Error Messages**: Prevents user enumeration during login/password reset
- **Account Change Logging**: All email/username/password updates logged with validated IP addresses
- **Session Persistence**: Users remain logged in after password change (re-authenticated)
- **Production Cache Validation**: Runtime warning if local memory cache used in production (config/settings.py:322-331)
- **Email Configuration Validation**: Validates DEFAULT_FROM_EMAIL is set before sending emails (home/views.py:177-185)
- **Email Retry Mechanism**: 3 retry attempts with exponential backoff (1s, 2s, 4s) for transient failures (home/views.py:190-217)

## Development Commands

### Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Install all dependencies (includes linting and security tools)
pip install -r requirements.txt

# Verify tools installed
pylint --version
bandit --version
pytest --version

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start dev server
python manage.py runserver
```

### Testing
```bash
# Run all tests with pytest
pytest

# Run Django tests
python manage.py test

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run specific test
pytest home/tests.py::TestClassName::test_method_name

# Test independence verification (pytest-random-order included in requirements.txt)
pytest --random-order         # Run tests in random order
pytest -x                     # Stop on first failure to debug test dependencies

# Mutation testing (mutmut included in requirements.txt)
mutmut run                    # Run mutation tests
mutmut results                # View mutation test results
mutmut show <mutation_id>     # Show specific mutation
mutmut html                   # Generate HTML report

# Fuzz testing (hypothesis included in requirements.txt)
# Add @given decorators to test functions in home/tests.py
# Example:
# from hypothesis import given
# from hypothesis.strategies import text, integers
# @given(text(), integers())
# def test_with_random_inputs(string_input, int_input):
#     # Test with randomly generated inputs

# Mocking tools (pytest-mock included in requirements.txt)
# Use unittest.mock.patch to mock external dependencies
# Example:
# from unittest.mock import patch, MagicMock
# @patch('home.views.send_mail')
# def test_email_sending(mock_send_mail):
#     mock_send_mail.return_value = 1
#     # Test code that calls send_mail

# Time mocking for deterministic tests (freezegun included in requirements.txt)
# from freezegun import freeze_time
# @freeze_time('2025-01-15 12:00:00')
# def test_time_dependent_feature():
#     # Test with fixed time
```

### Code Linting (Pylint)
```bash
# Pylint is included in requirements.txt

# Run pylint on specific files
pylint home/views.py
pylint home/models.py

# Run on entire app
pylint home/

# Run on entire project (home and config apps)
pylint home/ config/

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

**Note**: Pylint will be integrated into CI pipeline in Sprint 3. For Sprint 2, use it locally to maintain code quality.

### Database Operations
```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Check migration status
python manage.py showmigrations

# Django shell (for debugging)
python manage.py shell
```

### Admin Management
```bash
# Create superuser (admin account)
python manage.py createsuperuser

# Access admin panel
# Local: http://localhost:8000/admin/
# Production: https://language-learning-platform-xb6f.onrender.com/admin/
```

### DevEDU Environment
```bash
# Set environment variables for DevEDU proxy
export IS_DEVEDU=True
export STATIC_URL_PREFIX=/proxy/8000

# Run server in DevEDU
python manage.py runserver 0.0.0.0:8000

# Access via DevEDU proxy URL
# https://editor-jmanchester-20.devedu.io/proxy/8000/

# Configuration:
# - IS_DEVEDU=True enables proxy support
# - Sets FORCE_SCRIPT_NAME to /proxy/8000 (handles all URL generation)
# - Sets STATIC_URL to /proxy/8000/static/
# - Relaxes CSRF settings for development
```

### Email Testing (Password Reset / Username Recovery)
```bash
# College Project - Simulated Emails Displayed on Page
# Password reset and username recovery show simulated emails in styled boxes
# No SMTP configuration required - emails render directly on the forgot password/username pages
# This maintains demonstration value for college projects without SMTP access

# Production (if SMTP available) - Configure environment variables
# EMAIL_HOST=smtp.sendgrid.net (or other SMTP provider)
# EMAIL_PORT=587
# EMAIL_HOST_USER=apikey
# EMAIL_HOST_PASSWORD=<your-api-key>
# DEFAULT_FROM_EMAIL=noreply@yourdomain.com
# Note: Current implementation uses simulated email display, not actual SMTP sending
```

## Key Implementation Details

**Settings Behavior** (config/settings.py):
- Lines 30: IS_DEVEDU environment variable controls proxy configuration
- Lines 35-39: Auto-enables DEBUG for pytest/test runs to avoid SSL redirect issues
- Lines 172-178: DevEDU environment uses FORCE_SCRIPT_NAME for proxy URL handling
- Lines 192-209: Tests use simple StaticFilesStorage, production uses WhiteNoiseCompressedManifest
- Lines 258-270: Security headers only enabled when DEBUG=False

**User Progress Calculation**:
- Weekly stats query lessons/quizzes from last 7 days using `completed_at__gte`
- Progress views use `get_or_create()` to auto-initialize UserProgress
- Quiz accuracy = (total correct / total questions) * 100

## CI/CD

**GitHub Actions Workflows**:
- `.github/workflows/coverage.yml` - Runs pytest with coverage on all pushes/PRs, posts coverage comment to PRs
- `.github/workflows/ai-code-review.yml` - OpenAI code review on PRs when Python/HTML/JS/MD files change

**Test Requirements**:
- Uses pytest (configured in pytest.ini and conftest.py)
- Coverage reporting via pytest-cov
- `conftest.py` disables APPEND_SLASH for tests
- **Current Status**: 167 tests, 90% code coverage
- **Test Categories**:
  - Model tests (20 tests)
  - Authentication tests (39 tests including validation, rate limiting, redirect protection)
  - Account management tests (21 tests including edge cases)
  - Password recovery tests (14 tests)
  - Admin tests (36 tests)
  - Security tests (XSS, SQL injection, unauthorized access, input validation, user enumeration)
  - Rate limiting tests (brute force prevention)
  - Open redirect protection tests

## Deployment (Render)

**Configuration** (render.yaml):
- Build: `./build.sh` (installs deps, collects static, runs migrations)
- Start: `gunicorn config.wsgi:application`
- Auto-provisions PostgreSQL database
- **Auto-deploy: ENABLED** - Pushes to `main` automatically deploy to production
- Environment variables: SECRET_KEY (auto-generated), DEBUG=False, DATABASE_URL (from database)

**Production URL**: https://language-learning-platform-xb6f.onrender.com

**Deployment Process**:
- Push to `main` branch **automatically deploys** to production
- **Continuous Deployment (CD) Active:**
  1. Merge changes to `main` branch
  2. Render automatically detects the push
  3. Runs `./build.sh` (installs deps, collects static, runs migrations)
  4. Deploys new version if build succeeds
  5. Monitor build logs at [Render Dashboard](https://dashboard.render.com/)
- Changes go live automatically within ~2-5 minutes of merge

## Environment Variables

**Required for Production**:
- `SECRET_KEY` - Django secret (auto-generated by Render)
- `DEBUG` - Set to "False"
- `DATABASE_URL` - PostgreSQL connection string (auto-set by Render)

**Optional**:
- `RENDER_EXTERNAL_HOSTNAME` - Auto-set by Render, added to ALLOWED_HOSTS

**Local Development**: Django uses fallback values in settings.py, but you can create `.env` for overrides

## Agent Operating Principles

### Task Completion Standards
- Always verify your work before reporting completion
- Run tests after making code changes
- Check linting before finalizing changes (if configured)
- If you encounter errors, debug them - don't just report failure
- Provide specific file paths and line numbers in your final report
- Test your changes in the actual running application when possible

### Code Quality Requirements
- Write tests for new functionality (unit tests, integration tests, edge cases)
- **Ensure all tests are independent** - tests must pass when run individually or in any order
- **Prevent flaky tests** - use mocks for external dependencies (network, time, random, email)
- **Run pylint before committing** - maintain code quality with linting: `pylint home/ config/`
- **Single return statement**: Functions should return one thing when practical
  - Use guard clauses for early validation exits
  - Prefer single return at end for normal flow
  - Improves readability and reduces cognitive complexity
  - Exception: Early returns for validation/error conditions are acceptable
- Follow PEP 8 standards for Python code
- Follow Django best practices and conventions
- Match existing code style and patterns in the codebase
- Write clear, descriptive commit messages
- Write clear, descriptive, comprehensive docstrings in the Python code using line comments or block comments
- **See STYLE_GUIDE.md** for comprehensive coding standards
- **See SECURITY_GUIDE.md** for security best practices and scanning tools

### Testing Workflow
**REQUIRED WORKFLOW**: When making code changes, follow this exact order:
1. **Write/modify code** - Implement features or fixes
2. **Run Pylint** - Check code quality on modified files
   ```bash
   pylint home/views.py home/models.py home/forms.py --rcfile=.pylintrc
   ```
   - Target: 9.5+/10 score (current: 9.71-10.00/10)
   - Fix any critical issues before proceeding
3. **Run Bandit** - Security scan on modified files
   ```bash
   bandit -r home/views.py home/models.py home/forms.py -f txt
   ```
   - Target: 0 high/critical security issues
   - Address any security warnings before proceeding
4. **Fix linting/security issues** - Address any problems found in steps 2-3
5. **Run full test suite** - Verify all tests pass
   ```bash
   pytest
   ```
6. **Check coverage** - Ensure coverage remains high
   ```bash
   pytest --cov=. --cov-report=term-missing
   ```
   - Target: 90%+ coverage
7. **Manual testing** - Test in browser when UI changes are involved
8. **Commit & push** - Once everything passes

This workflow ensures code quality and security issues are caught before running the test suite, making development more efficient.

**For Critical/Security Code (authentication, input validation, permissions):**
7. Run mutation testing: `mutmut run` to verify tests catch actual bugs
8. Add fuzz testing with `hypothesis` to discover edge cases with random inputs
9. Review mutation survivors and add tests to catch them
10. Ensure mutation score >80% for security-critical modules

## Common Task Patterns

### Adding New Features
1. Understand the requirement and architecture (review this file)
2. Identify which files need changes (models, views, forms, templates, urls)
3. Check existing similar features for patterns
4. Implement changes following Django conventions:
   - **Models**: Add to `home/models.py` (or create new app if major feature)
   - **Views**: Add to `home/views.py`
   - **URLs**: Update `home/urls.py`
   - **Templates**: Add to `home/templates/`
   - **Forms**: Add to `home/forms.py` if needed
5. Write tests in `home/tests.py`
6. Run migrations if models changed: `python manage.py makemigrations && python manage.py migrate`
7. Run tests: `pytest`
8. Verify manually in browser
9. Document any new environment variables or setup steps

### Bug Fixing
1. Reproduce the bug (check tests or manual verification)
2. Identify root cause using search/read tools
3. Fix the issue
4. Add test case to prevent regression
   - Ensure test is independent (doesn't rely on other tests)
   - Mock external dependencies to prevent flakiness
   - Test should fail before the fix and pass after
5. Verify fix with full test suite: `pytest`
6. Run tests in random order to verify independence: `pytest --random-order`
7. Report: what was broken, what you changed, which test proves it's fixed

### Refactoring
1. Understand current implementation thoroughly
2. Write tests for current behavior if coverage is lacking
   - Ensure tests are independent and not flaky
3. Make incremental changes
4. Run tests after each change: `pytest`
5. Verify test independence: `pytest --random-order`
6. Ensure no functionality is lost
7. Report: what you refactored, why, and test results

### Search and Analysis Tasks
When searching for code or analyzing the codebase:
1. Use search tools to find code patterns and files
2. Read relevant files completely, not just snippets
3. Trace function calls across files
4. Check both backend logic (views.py, models.py) and frontend (templates/)
5. Report findings with specific file:line references

## Common Development Patterns

### Adding a New Model
1. Add to `home/models.py` (or create new app with `python manage.py startapp appname`)
2. Run `python manage.py makemigrations`
3. Run `python manage.py migrate`
4. Register in `home/admin.py` for admin interface (optional)
5. Add tests in `home/tests.py`
6. Verify in Django shell or admin panel

### Adding a New View
1. Add function or class-based view to `home/views.py`
2. Add URL pattern to `home/urls.py`
3. Create template in `home/templates/`
4. Add test to verify view response and context
5. Test manually in browser

### Working with Tests
- Pytest is primary test runner (see pytest.ini)
- Django's manage.py test also works
- Always run tests after changes: `pytest`
- Check coverage: `pytest --cov=.`
- Write tests for edge cases and error handling
- Use Django's TestCase for database-dependent tests
- Use fixtures for common test data

**Test Quality Requirements:**
- **Test Independence**: Every test must be completely independent
  - Tests should pass when run individually or in any order
  - Use `setUp()` and `tearDown()` methods or pytest fixtures to ensure clean state
  - Clear cache between tests (`cache.clear()`) to prevent state leakage
  - Create fresh test data for each test, never rely on data from previous tests
  - Avoid global state or shared mutable objects
  - Run tests in random order to detect dependencies: `pytest --random-order`
- **Prevent Flaky Tests**: Tests must be deterministic and reliable
  - **Mock external dependencies**: Use `unittest.mock` or `pytest-mock` for:
    - Network calls (APIs, external services)
    - Email sending (SMTP)
    - File system operations (when testing logic, not I/O)
    - Time-dependent behavior (`datetime.now()`, `timezone.now()`)
    - Random number generation
  - **Use freezegun** for time-dependent tests: `@freeze_time('2025-01-15')`
  - **Avoid sleep()**: Never use `time.sleep()` in tests; use mocks or timeouts
  - **Fix random seeds**: If using random data, set seed: `random.seed(42)`
  - **Mock third-party services**: Don't make real HTTP requests in tests
  - **Database state**: Use Django's TestCase for automatic transaction rollback
  - **Clean up resources**: Close files, connections, temp directories in tearDown

**Advanced Testing Techniques:**
- **Mutation Testing**: Use `mutmut` to verify test quality by introducing small code changes (mutations) and ensuring tests catch them. This validates that tests actually detect bugs, not just provide coverage.
  - Run mutation testing on critical security code (authentication, input validation, permissions)
  - Aim for high mutation score (>80%) on security-sensitive modules
  - Use mutation testing to find weak tests that don't actually verify behavior
- **Fuzz Testing**: Use `hypothesis` to generate random test inputs and discover edge cases
  - Apply to input validation functions (login, signup, account updates)
  - Use for data parsing and serialization functions
  - Particularly valuable for security-critical code paths
  - Define strategies that match your domain (email formats, usernames, passwords)
  - Run fuzz tests in CI to catch unexpected edge cases

## Error Handling

If you encounter errors:
1. **Test failures**: Read the full traceback, identify the failing assertion, fix root cause
2. **Import errors**: Check requirements.txt, verify file structure, check Python path
3. **Migration errors**: Check for conflicting migrations, review migration files, try `python manage.py makemigrations --merge` if needed
4. **Database errors**: Check DATABASE_URL, verify migrations ran, check model definitions
5. **Template errors**: Check template syntax, verify template paths, check context variables
6. **Static file errors**: Run `python manage.py collectstatic`, check STATIC_URL and STATIC_ROOT settings
7. **Deployment errors**: Check Render logs, verify environment variables, check build.sh script

## Reporting Results

Your final report should include:
- **Summary**: What you accomplished in 2-3 sentences
- **Files changed**: List with file:line references for key changes
- **Tests**: Did tests pass? Coverage percentage?
- **Verification**: How did you verify your work?
- **Issues**: Any blockers or problems encountered?
- **Next steps**: What remains to be done (if task is incomplete)?

### Good Report Example
```
Successfully implemented vocabulary practice feature with spaced repetition algorithm.

Files changed:
- home/models.py:145 - Added VocabularyCard and Review models with spaced repetition fields
- home/views.py:289 - Added PracticeView with next card selection logic
- home/urls.py:23 - Added /vocabulary/practice/ route
- home/tests.py:456 - Added test_vocabulary_practice and test_spaced_repetition_algorithm
- home/templates/vocabulary_practice.html - Created practice interface with flip card UI

Tests: All passed (78 tests). Coverage: 87% (above target).

Verification: 
- Tested vocabulary practice flow manually in browser
- Verified spaced repetition algorithm with unit tests
- Checked database queries are optimized (select_related used)
- Tested on both SQLite (dev) and PostgreSQL (staging)

Next steps: Add audio pronunciation feature for vocabulary cards.
```

### Poor Report Example
```
I made some changes to the views file and added stuff. It might work but I'm not sure. There were some errors but I tried to fix them.
```

## Security Considerations

### Implemented Security Features
- **IP Address Validation**: Python ipaddress module validates format to prevent injection attacks (home/views.py:39-87)
  - Falls back to REMOTE_ADDR if X-Forwarded-For is invalid
  - Logs warnings for malformed IP addresses
  - Returns 'unknown' for unparseable addresses
- **Login Attempt Logging**: All authentication events logged with validated IP addresses
- **Open Redirect Prevention**: Login redirects validated with `url_has_allowed_host_and_scheme()`
- **Password Validation**: Django's built-in validators enforce strong passwords (min 8 chars, complexity)
- **Email Validation**: Format validation before account creation
- **Secure Password Reset**: Token expires after 20 minutes; admin generates 12-char random passwords
- **Generic Error Messages**: Prevents user enumeration during login/password reset
- **CSRF Protection**: Django's built-in CSRF protection on all forms
- **Rate Limiting**: 5 login attempts per 5 minutes per IP to prevent brute force attacks (home/views.py:328-345)
  - Tracks attempts via Django cache framework
  - IP-based rate limiting with automatic expiration
  - Graceful handling of cache backends without TTL support
  - Clear error messages with retry-after timing
- **Input Validation & Sanitization**: Comprehensive multi-layer validation (home/views.py:350-371)
  - Empty field checks for all required inputs
  - Length limits (max 254 chars for username/email per RFC 5321)
  - Character whitelist (alphanumeric + @._+- for safe email/username characters)
  - Prevents injection attacks, XSS, and SQL injection attempts
  - User input stripped of whitespace before validation
- **XSS Protection**: Django's automatic HTML escaping + input character whitelist (verified via test suite)
- **SQL Injection Protection**: Django ORM parameterized queries + input validation (verified via test suite)
- **Production Cache Warning**: Runtime validation prevents local memory cache in production
- **Email Configuration Validation**: Validates DEFAULT_FROM_EMAIL before sending
- **Email Retry Mechanism**: Exponential backoff for transient SMTP failures

### Best Practices to Follow
- Never commit secrets or API keys to the repository
- Use environment variables for sensitive data (.env for local, Render dashboard for production)
- Validate all user input in forms
- Use Django's authentication system for user management
- Sanitize any user-generated content displayed in templates
- Keep dependencies updated (check for security vulnerabilities with `pip list --outdated`)
- Use HTTPS in production (Render provides this automatically)
- Set secure cookie settings when DEBUG=False
- Monitor login attempt logs for suspicious activity

### Cache Security (Redis/Memcached for Production)
When deploying with Redis or Memcached:
- **Redis Security**:
  - Use password authentication (requirepass in redis.conf)
  - Bind Redis to localhost or use firewall rules to restrict access
  - Use TLS for connections over public networks
  - Regularly update Redis to patch security vulnerabilities
  - Include PASSWORD in Django CACHES configuration
- **Memcached Security**:
  - Bind to localhost or use firewall to restrict access
  - Use SASL authentication if available
- **Production Deployment**:
  - Never use local memory cache in production (runtime warning enabled)
  - Configure Redis/Memcached via environment variables
  - See config/settings.py:280-331 for detailed configuration examples

## Performance Notes

### Implemented Optimizations
- **Database Query Optimization**: `get_weekly_stats()` reuses queryset to avoid duplicate queries (home/models.py:45-49)
- **Static File Compression**: WhiteNoise with CompressedManifestStaticFilesStorage in production
- **Connection Pooling**: PostgreSQL connection max_age=600 for connection reuse

### Best Practices to Follow
- Use `select_related()` and `prefetch_related()` for database query optimization
- Consider caching for frequently accessed data
- Be mindful of N+1 query problems
- Use database indexes for frequently queried fields
- Monitor query counts in Django Debug Toolbar (development)
- Consider pagination for large querysets

## Getting Unstuck

If you're stuck:
1. Review this file for architecture overview
2. Search for similar existing functionality in the codebase
3. Check Django documentation: https://docs.djangoproject.com/
4. Look at test files to understand expected behavior
5. Check Render logs if deployment issues occur
6. Review GitHub Actions logs if CI/CD fails
7. Use Django shell to test queries interactively: `python manage.py shell`
8. Check settings.py for configuration issues
9. Look at existing views/models for patterns to follow
10. Ask specific questions with context about what you've tried

## Django-Specific Best Practices

### Model Guidelines
- Use descriptive field names
- Add `__str__` methods to all models for admin readability
- Use appropriate field types (CharField, TextField, DateTimeField, etc.)
- Add `verbose_name` and `help_text` for clarity
- Use `related_name` for reverse relations
- Add model-level validation in `clean()` method when needed

### View Guidelines
- Use class-based views for standard CRUD operations
- Use function-based views for simple or custom logic
- Always validate and sanitize user input
- Use `@login_required` decorator or `LoginRequiredMixin` for protected views
- Return appropriate HTTP status codes
- Handle exceptions gracefully

### Template Guidelines
- Use template inheritance with base templates
- Use `{% load static %}` for static files
- Use `{% url %}` tag for URL generation (never hardcode URLs)
- Escape user content properly (Django does this by default)
- Keep logic in views, not templates
- Use template filters for formatting

### URL Guidelines
- Use descriptive URL names for reverse lookups
- Group related URLs together
- Use path converters (`<int:pk>`, `<slug:slug>`, etc.)
- Keep URLs RESTful and intuitive

## Project-Specific Notes

### Authentication System
- Flexible login (users can enter username or email, system authenticates by username)
- Usernames auto-generated from email prefix during signup
- Number suffix added for duplicates (e.g., john, john2, john3)
- Login/signup use same template with different form handling

### Progress Tracking System
- `UserProgress` model stores user learning stats
- Auto-created on first access with `get_or_create()`
- Weekly stats calculated from last 7 days of data
- Quiz accuracy = (sum of correct answers / sum of total questions) * 100

### Static Files Handling
- Development: Django serves static files (DEBUG=True only)
- Production: WhiteNoise with compression and caching
- DevEDU: Uses IS_DEVEDU env var, sets FORCE_SCRIPT_NAME to `/proxy/8000` for all URLs
- Tests: Simplified storage backend for speed
- **Security**: Static file serving via Django disabled in production (WhiteNoise handles it)

### Database Configuration
- Automatic switching between SQLite (dev) and PostgreSQL (prod)
- Tests always use SQLite for speed
- Migrations applied automatically on Render deployment via build.sh

### Admin Interface
- Django admin at `/admin/` with enhanced user management and unified navigation
- **Unified UI**: Admin panel uses same purple gradient navigation as main site (no Django header)
- **Staff-Only Access**: Admin button visible only to staff users in navigation bar
- Custom admin actions for bulk operations (see home/admin.py)
- **Creating admin**: `python manage.py createsuperuser` (local) or via Render Shell (production)
- **Admin capabilities**:
  - Reset user passwords (generates secure 12-char random passwords)
  - Make users administrators or remove admin privileges
  - Reset user progress (deletes lessons, quizzes, resets stats)
  - View user progress summary in User detail page
  - Search/filter all users, progress, lessons, and quizzes
- **Security**: Login attempts logged with IP addresses for monitoring
- See [ADMIN_GUIDE.md](ADMIN_GUIDE.md) for complete admin documentation

---

**Last Updated**: 29 October 2025
**Maintained By**: Development Team

## Recent Updates

### Sprint 3 - User Profile Avatars & Email Simulation (29 October 2025)
- **User Profile System** (home/models.py, home/forms.py):
  - Added UserProfile model with one-to-one relationship to User
  - Automatic profile creation via Django signals
  - Avatar upload with ImageField (PNG/JPG, 5MB max)
  - Automatic image resize to 200x200px with Pillow
  - Gravatar fallback using MD5 email hash (usedforsecurity=False)
  - Form validation for file type and size
- **Avatar Display** (templates, CSS):
  - Navigation bar: 32px circular avatars (positioned left of Home button)
  - Account page: 80px avatar with upload form
  - Progress page: 120px header avatar
  - Dashboard: 200px hero avatar
  - Responsive CSS styling for all avatar sizes
- **Email Simulation** (home/views.py, templates):
  - Password reset displays simulated email in styled box (no SMTP required)
  - Username recovery displays simulated email in styled box
  - Gradient background styling for email display
  - Maintains security (doesn't reveal if user exists)
  - College project friendly (Render doesn't provide SMTP)
- **Security Compliance**:
  - Bandit scan: 0 security issues (fixed MD5 usedforsecurity flag)
  - Pylint: 9.71-10.00/10 code quality scores
  - All 167 tests passing, 90% coverage maintained
- **Development Workflow Update**:
  - New required workflow: Code → Pylint → Bandit → Fix Issues → Tests → Commit
  - Ensures quality and security checks before test execution
- **Admin Updates**:
  - UserProfile inline added to User admin
  - Avatar management in admin interface
  - **Content Moderation** for offensive/obscene avatars:
    - Admin action to delete avatars from UserProfile admin
    - Admin action to delete avatars from User admin (convenience wrapper)
    - Avatar preview in admin (100x100px, shows Gravatar fallback)
    - "Has Avatar" column in UserProfile list view
    - Security logging for deletions with admin username
    - Proper file deletion from storage
    - Users automatically fall back to Gravatar
- **Documentation**:
  - Updated CLAUDE.md with avatar system and simulated emails
  - Updated testing workflow with lint and security requirements

### Login Security Enhancements (26 October 2025)
- **Username or Email Login**: Users can now log in with either username or email
- **Rate Limiting** (home/views.py:328-345):
  - 5 login attempts per 5 minutes per IP
  - Prevents brute force attacks
  - Graceful cache backend handling (supports LocMemCache and Redis)
  - Clear error messages with retry-after timing
- **Comprehensive Input Validation** (home/views.py:350-371):
  - Empty field validation for username/email and password
  - Length limits (max 254 characters per RFC 5321)
  - Character whitelist (alphanumeric + @._+- only)
  - Prevents XSS, SQL injection, and other injection attacks
  - Generic error messages to prevent user enumeration
- **Open Redirect Protection** (home/views.py:405-413):
  - Django's `url_has_allowed_host_and_scheme()` validates redirect URLs
  - Only allows redirects to same host
  - Requires HTTPS in secure contexts
  - Falls back to landing page for invalid redirects
- **Client-Side Protection** (home/templates/login.html:59-70):
  - HTML5 pattern attribute matches backend validation
  - Maxlength attribute enforces 254 char limit
  - User-friendly validation messages
  - Help text for acceptable characters
- **Testing**:
  - 9 new security tests (rate limiting, open redirects, user enumeration, input validation)
  - Improved test quality with `assertContains()` for better error checking
  - Cache clearing between tests to prevent test interference
  - **Total: 167 tests with 93% code coverage**
  - Verified all injection attack scenarios blocked
- **Documentation**:
  - Updated CLAUDE.md with comprehensive security details
  - Updated USER_GUIDE.md to reflect username/email login

### Comprehensive Code Quality & Security Improvements (26 October 2025)
- **Security Enhancements**:
  - IP address format validation to prevent injection attacks
  - Production cache backend validation with runtime warnings
  - Email configuration validation (DEFAULT_FROM_EMAIL)
  - Email retry mechanism with exponential backoff (1s, 2s, 4s delays)
  - Verified XSS and SQL injection protection via test suite
- **Documentation Improvements**:
  - Comprehensive Redis/Memcached security documentation
  - Enhanced CSS comments explaining "why" not just "what"
  - PEP 257 compliant docstrings with Args/Returns sections
  - Production deployment warnings and best practices
- **Testing Improvements**:
  - 7 new edge case tests (invalid actions, XSS, SQL injection, unauthorized access, etc.)
  - Query optimization verification with assertNumQueries
  - **Total: 129 tests with 89% code coverage**
- **UX/UI Fixes**:
  - Fixed negative margin responsive layout issue (changed to 0.5rem)
  - Better visual hierarchy for forgot username/password links
- **Reliability**:
  - Email sending retry mechanism improves production resilience
  - Exponential backoff for transient SMTP failures
  - Comprehensive error logging with attempt tracking

### Account Management System (26 October 2025)
- **Account Settings Page**: Users can update email, name, username, and password
- **Password Recovery**: Email-based password reset with secure tokens (20-min expiration)
- **Username Recovery**: Email reminder for forgotten usernames
- **Email Configuration**: Console backend for dev, SMTP for production
- **Security Features**:
  - Token-based password reset with 20-minute expiration
  - All account changes logged with IP addresses
  - Password verification required for email/password updates
  - Generic messages to prevent user enumeration
  - Session persistence after password change
- **Testing**: 32 comprehensive tests for account features
- **UI/UX**: Soft gray card backgrounds, forms stay visible after submission
- **Documentation**: See USER_GUIDE.md for end-user documentation

### Admin Panel Enhancements (25 October 2025)
- Added unified navigation across admin and main site (purple gradient header)
- Staff-only admin button in navigation bar
- Custom logout handler for proxy environment compatibility
- Secure random password generation for admin password resets

### Security Improvements
- Login attempt logging with IP addresses for security monitoring
- Open redirect prevention in login flow
- Django password validators (min 8 chars, complexity requirements)
- Email format validation
- Generic error messages to prevent user enumeration
- Account change logging with IP addresses

### Performance Optimizations
- Eliminated duplicate database queries in weekly stats calculation
- Optimized queryset reuse in UserProgress.get_weekly_stats()

### DevEDU Support
- Simplified proxy configuration using IS_DEVEDU environment variable
- FORCE_SCRIPT_NAME handles all URL generation in proxy environments
- Proper CSRF configuration for development proxies

### Code Quality
- Comprehensive docstrings for all view functions
- Module-level documentation in config/urls.py
- Enhanced security comments and warnings
- Template comments explaining customizations
