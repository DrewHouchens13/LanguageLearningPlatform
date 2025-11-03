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

**Database**: Automatic switching between SQLite (dev) and PostgreSQL (prod) via `DATABASE_URL` environment variable

**Key Features**:
- Flexible login (username or email accepted)
- User profiles with avatar uploads (PNG/JPG, 5MB max, auto-resized to 200x200px)
- Gravatar fallback using MD5 hash (usedforsecurity=False)
- Progress tracking with weekly stats calculation
- Password recovery with secure tokens (20-min expiration)
- Simulated email display for college projects (no SMTP required)
- Admin interface with unified navigation and bulk operations

## Quick Start Commands

### Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start dev server
python manage.py runserver
```

### Testing & Quality Checks
```bash
# Required workflow: Pylint → Bandit → Tests → Commit

# 1. Run Pylint (target: 9.5+/10)
pylint home/views.py home/models.py home/forms.py --rcfile=.pylintrc

# 2. Run Bandit security scan (target: 0 high/critical issues)
bandit -r home/views.py home/models.py home/forms.py -f txt

# 3. Run full test suite (current: 167 tests, 90% coverage)
pytest

# 4. Check coverage
pytest --cov=. --cov-report=term-missing

# 5. Verify test independence
pytest --random-order
```

**See [TESTING_GUIDE.md](TESTING_GUIDE.md) for comprehensive testing documentation.**

### Database Operations
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Django shell (debugging)
python manage.py shell
```

## Key Implementation Details

### Authentication & Security
- Username/email login with rate limiting (5 attempts per 5 min per IP)
- Input validation with character whitelist (prevents XSS, SQL injection)
- Open redirect prevention using Django's `url_has_allowed_host_and_scheme()`
- IP address validation to prevent injection attacks
- All account changes logged with IP addresses

### Progress Tracking
- `UserProgress.get_weekly_stats()` - Weekly minutes, lessons, quiz accuracy from last 7 days
- `UserProgress.calculate_quiz_accuracy()` - Overall accuracy: (correct / total) * 100
- Auto-created on first access with `get_or_create()`

### Admin Interface
- Custom User admin with bulk actions (reset passwords, make/remove admins, reset progress)
- UserProfile inline for avatar management
- Unified purple gradient navigation matching main site
- Staff-only admin button in navigation bar
- **See [ADMIN_GUIDE.md](ADMIN_GUIDE.md) for complete admin documentation**

### Static Files & Media
- Development: Django serves static files (DEBUG=True)
- Production: WhiteNoise with compression
- DevEDU: Set `IS_DEVEDU=True` and `FORCE_SCRIPT_NAME=/proxy/8000`
- Media files: Avatar uploads stored in `media/avatars/user_{id}/`

## Agent Operating Principles

### Task Completion Standards
- Always verify work before reporting completion
- Run tests after code changes (follow testing workflow)
- Provide specific file paths and line numbers in final report
- Debug errors - don't just report failure
- Test changes in browser when applicable

### Code Quality Requirements
- Write tests for new functionality (unit, integration, edge cases)
- **Ensure test independence** - must pass in any order (`pytest --random-order`)
- **Prevent flaky tests** - mock external dependencies (network, time, email)
- **Follow required workflow**: Code → Pylint → Bandit → Fix → Tests → Commit
- Follow PEP 8 and Django best practices
- Match existing code style
- **See [STYLE_GUIDE.md](STYLE_GUIDE.md)** for comprehensive coding standards
- **See [SECURITY_GUIDE.md](SECURITY_GUIDE.md)** for security best practices
- **See [TESTING_GUIDE.md](TESTING_GUIDE.md)** for testing guidelines

### Critical Security Code
For authentication, input validation, and permissions:
1. Run mutation testing: `mutmut run` (target: >80% mutation score)
2. Add fuzz testing with `hypothesis` for random input edge cases
3. Review mutation survivors and add tests

## Common Task Patterns

### Adding New Features
1. Review architecture and identify files to change
2. Implement following Django conventions:
   - **Models**: `home/models.py`
   - **Views**: `home/views.py`
   - **URLs**: `home/urls.py`
   - **Templates**: `home/templates/`
   - **Forms**: `home/forms.py`
3. Write tests in `home/tests.py`
4. Run migrations if models changed
5. Follow testing workflow (Pylint → Bandit → Tests)
6. Verify manually in browser

### Bug Fixing
1. Reproduce bug
2. Identify root cause
3. Write test that fails (demonstrates bug)
4. Fix issue
5. Ensure test passes and is independent
6. Run full test suite
7. Report: what broke, what changed, which test proves fix

### Django Patterns
**Adding a Model**: Edit models.py → makemigrations → migrate → register in admin.py → write tests

**Adding a View**: Edit views.py → add URL pattern → create template → write tests → test in browser

**Testing**: Use Django's TestCase for database tests, pytest for others, mock external dependencies

## Deployment

**Production URL**: https://language-learning-platform-xb6f.onrender.com

**Auto-Deploy**: Pushes to `main` branch automatically deploy to production (2-5 minutes)

**Configuration**: See render.yaml and build.sh

**Environment Variables**:
- Production: `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL` (auto-set by Render)
- DevEDU: `IS_DEVEDU=True`, `STATIC_URL_PREFIX=/proxy/8000`

**See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment documentation.**

## Error Handling

Common errors and solutions:
1. **Test failures**: Read traceback, identify assertion, fix root cause
2. **Import errors**: Check requirements.txt, verify file structure
3. **Migration errors**: Check for conflicts, try `makemigrations --merge`
4. **Database errors**: Check DATABASE_URL, verify migrations
5. **Template errors**: Check syntax, paths, context variables
6. **Deployment errors**: Check Render logs, verify env vars

## Reporting Results

Include in final report:
- **Summary**: 2-3 sentence accomplishment
- **Files changed**: List with file:line references
- **Tests**: Pass/fail status, coverage percentage
- **Verification**: How you verified work
- **Issues**: Blockers or problems
- **Next steps**: Remaining work (if incomplete)

## Getting Unstuck

1. Review this file for architecture overview
2. Search for similar functionality in codebase
3. Check Django documentation: https://docs.djangoproject.com/
4. Look at test files for expected behavior
5. Check Render logs for deployment issues
6. Use Django shell: `python manage.py shell`
7. Review settings.py for configuration

## Documentation Reference

- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Comprehensive testing documentation (mutation testing, fuzz testing, mocking, test independence)
- **[SECURITY_GUIDE.md](SECURITY_GUIDE.md)** - Security best practices and scanning tools
- **[STYLE_GUIDE.md](STYLE_GUIDE.md)** - Coding standards and style conventions
- **[ADMIN_GUIDE.md](ADMIN_GUIDE.md)** - Admin interface documentation
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment and CI/CD documentation
- **[USER_GUIDE.md](USER_GUIDE.md)** - End-user documentation

## Recent Updates (Last 2 Sprints)

### Sprint 3 - User Profile Avatars & Email Simulation (29 October 2025)
- **User Profile System**: UserProfile model with avatar upload (PNG/JPG, 5MB max, auto-resize to 200x200px), Gravatar fallback
- **Avatar Display**: Multiple sizes (32px nav, 80px account, 120px progress, 200px dashboard)
- **Email Simulation**: Password reset and username recovery show simulated emails in styled boxes (no SMTP required)
- **Admin Content Moderation**: Delete offensive avatars with security logging
- **Development Workflow**: New required workflow (Code → Pylint → Bandit → Fix → Tests → Commit)
- **Security**: Bandit scan 0 issues, Pylint 9.71-10.00/10, 167 tests, 90% coverage

### Login Security Enhancements (26 October 2025)
- **Username or Email Login**: Users can log in with either
- **Rate Limiting**: 5 attempts per 5 min per IP (prevents brute force)
- **Input Validation**: Character whitelist, length limits, prevents XSS/SQL injection
- **Open Redirect Protection**: Django's `url_has_allowed_host_and_scheme()`
- **Testing**: 9 new security tests, 167 total tests, 93% coverage

### Account Management System (26 October 2025)
- **Account Settings**: Update email, name, username, password
- **Password Recovery**: Email-based reset with secure tokens (20-min expiration)
- **Username Recovery**: Email reminder for forgotten usernames
- **Security**: All changes logged with IP addresses, password verification required
- **Testing**: 32 comprehensive tests for account features

---

**Last Updated**: 3 November 2025
**Maintained By**: Development Team
