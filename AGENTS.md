# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered interview practice platform called "Active Interview Service". It's a Django web application that allows users to practice job interviews with an OpenAI-powered interviewer. The system analyzes uploaded resumes and job listings to generate personalized interview questions and provide timed practice sessions.

## Core Architecture

### Application Structure
- **Django monolith**: Single Django app (`active_interview_app`) within project (`active_interview_project`)
- **Backend location**: All Django code is in `active_interview_backend/`
- **Deployment**: Docker Compose with Django + Gunicorn + Nginx
- **Database**: SQLite (stored in `active_interview_backend/db/`)
- **Static files**: Served through Nginx in production, collected to `staticfiles/`

### Key Models (active_interview_backend/active_interview_app/models.py)
- **UploadedResume**: User's resume files with extracted text content
- **UploadedJobListing**: Job posting documents with extracted text
- **Chat**: Interview session containing messages (JSON), key questions (JSON), difficulty (1-10), type (General/Industry Skills/Personality/Final Screening), and foreign keys to resume/job listing

### OpenAI Integration
- Uses OpenAI GPT-4o model for interview conversation
- System prompts generated dynamically based on resume, job listing, difficulty, and interview type
- AI generates 10 timed key questions per interview session
- Located primarily in views.py (ChatView, RestartChat, KeyQuestionsView)
- Max tokens: 15000 (defined in views.py)
- Client initialized at module level: `client = OpenAI(api_key=settings.OPENAI_API_KEY)`

### File Processing
- PDF files: Extracted with pymupdf4llm
- DOCX files: Extracted with python-docx
- File validation with filetype library
- Files saved to media/uploads/ directory
- Text content stored in model fields for AI processing

## Environment Setup

### Required Environment Variables
- `DJANGO_SECRET_KEY`: Django secret (auto-generated in dev if PROD=false)
- `OPENAI_API_KEY`: Required for AI interview functionality
- `PROD`: Set to "false" for development, "true" for production

### Local Development (Manual)
```bash
# From project root
python3 -m venv myenv
source myenv/bin/activate  # or .\myenv\bin\activate on Windows PowerShell

# Navigate to backend
cd active_interview_backend
pip install -r requirements.txt

# Generate secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Set environment variables
export PROD=false
export DJANGO_SECRET_KEY='<your-secret-key>'
export OPENAI_API_KEY=<your-api-key>

# Run migrations and start server
python3 manage.py migrate
python3 manage.py runserver
```

### Docker Compose Development
```bash
# From project root
# Create .env file with DJANGO_SECRET_KEY and OPENAI_API_KEY
docker-compose up -d --build
```

Access at: `http://127.0.0.1:8000` (manual) or `http://127.0.0.1` (Docker)

### Initial Account Setup
After first run, create a superuser and configure permissions:
```bash
python manage.py createsuperuser
# Access admin at http://127.0.0.1:8000/admin
# Create group called "average_role" with desired permissions
```

## File Organization

### Django Structure
- **Models**: `active_interview_backend/active_interview_app/models.py`
- **Views**: `active_interview_backend/active_interview_app/views.py` (large file, ~900 lines)
- **URLs**: `active_interview_backend/active_interview_app/urls.py`
- **Forms**: `active_interview_backend/active_interview_app/forms.py`
- **Templates**: `active_interview_backend/active_interview_app/templates/`
- **Tests**: `active_interview_backend/active_interview_app/tests/`
- **BDD Features**: `active_interview_backend/features/` (Gherkin user stories)
- **Step Definitions**: `active_interview_backend/active_interview_app/tests/steps/`
- **Settings**: `active_interview_backend/active_interview_project/settings.py`

### URL Structure
Key routes (defined in `active_interview_backend/active_interview_app/urls.py`):
- `/` - Homepage
- `/accounts/login/` - User login
- `/accounts/register/` - User registration
- `/profile/` - User profile with document management
- `/chat/` - Interview session list
- `/chat/create/` - Create new interview
- `/chat/<id>/` - Active interview view (AJAX-based)
- `/chat/<id>/edit/` - Edit interview settings
- `/chat/<id>/restart/` - Restart interview session
- `/chat/<id>/results/` - View interview results/charts
- `/document/` - Document list (resumes and job postings)
- `/upload-file/` - File upload endpoint

## Testing

### Running Tests
```bash
# From active_interview_backend/
python3 manage.py test

# With coverage
coverage run manage.py test
coverage report -m
```

### Test Structure
- All tests in `active_interview_backend/active_interview_app/tests/`
- `test_chat.py`: Chat/interview session tests
- `test_upload.py`: File upload and document management tests
- `test_e2e.py`: End-to-end Selenium tests
- `test.py`: Basic functionality tests

### BDD Feature Files
- Feature files (Gherkin): `active_interview_backend/features/`
- Step definitions: `active_interview_backend/active_interview_app/tests/steps/`
- Feature files document user stories and acceptance criteria
- Use behave or pytest-bdd for running BDD scenarios
- Keep related scenarios together in one feature file
- Use tags to map scenarios to GitHub issues

### Coverage Requirements
- Minimum 80% coverage enforced by CI
- Configuration in `.coveragerc`: excludes tests/, migrations/, __init__.py, manage.py
- Check script: `scripts/check-coverage.sh coverage_report.txt`

## Agent Operating Principles

### Task Completion Standards
- Always verify your work before reporting completion
- Run tests after making code changes
- Check linting before finalizing changes
- If you encounter errors, debug them - don't just report failure
- Provide specific file paths and line numbers in your final report

### Code Quality Requirements
- Maintain 80% test coverage - write tests for new functionality
- Follow flake8 standards for Python code
- Follow djlint standards for Django templates
- Match existing code style and patterns in the codebase

### Testing Workflow
When making code changes:
1. Make your changes
2. Run relevant tests: `cd active_interview_backend && python3 manage.py test`
3. Run BDD scenarios if applicable: `behave` or `pytest --bdd`
4. Check coverage: `coverage run manage.py test && coverage report -m`
5. Run linting: `flake8 --config .flake8 .` (from backend directory)
6. Fix any failures before reporting completion

## Common Task Patterns

### Adding New Features
1. Check if a feature file exists in `features/` directory - review user stories and acceptance criteria
2. Understand the architecture (review this file)
3. Identify which files need changes (models, views, forms, templates, urls)
4. Check existing similar features for patterns
5. Implement changes following Django conventions
6. Write unit tests in `active_interview_backend/active_interview_app/tests/`
7. Implement step definitions if working from Gherkin scenarios
8. Update URLs in `urls.py` if adding new routes
9. Run migrations if models changed: `python3 manage.py makemigrations && python3 manage.py migrate`
10. Verify with tests and linting

### Bug Fixing
1. Reproduce the bug (check tests or manual verification)
2. Identify root cause using grep/read tools
3. Fix the issue
4. Add test case to prevent regression
5. Verify fix with full test suite
6. Report: what was broken, what you changed, which test proves it's fixed

### Refactoring
1. Understand current implementation thoroughly
2. Write tests for current behavior if coverage is lacking
3. Make incremental changes
4. Run tests after each change
5. Ensure no functionality is lost
6. Report: what you refactored, why, and test results

### Search and Analysis Tasks
When searching for code or analyzing the codebase:
1. Use Grep for code patterns, Glob for file discovery
2. Read relevant files completely, not just snippets
3. Trace function calls across files
4. Check both backend logic (views.py) and frontend (templates/)
5. Report findings with specific file:line references

### Working with BDD Feature Files
When creating or implementing features:
1. **Writing feature files**: Place in `active_interview_backend/features/`
   - Use proper Gherkin syntax (Feature, Scenario, Given/When/Then)
   - Keep scenarios focused and independent
   - Group related scenarios in one feature file
   - Use descriptive scenario names
   - Use tags to link to GitHub issues (e.g., @issue-123)
2. **Implementing step definitions**: Place in `active_interview_backend/active_interview_app/tests/steps/`
   - Create separate step files for different feature areas (e.g., `authentication_steps.py`, `chat_steps.py`)
   - Reuse step definitions across scenarios when possible
   - Keep step implementations focused on test logic, not business logic
3. **Running BDD tests**: Use `behave` (recommended) or `pytest-bdd`
   - Behave: `cd active_interview_backend && behave`
   - Run specific tags: `behave --tags=issue-123`
   - Pytest-bdd: `cd active_interview_backend && pytest --bdd`
4. **Integration with unit tests**: BDD scenarios complement but don't replace unit tests
   - Use BDD for user-facing acceptance criteria
   - Use unit tests for implementation details and edge cases

## Django-Specific Guidance

### Django Conventions in This Project
- Uses class-based views (LoginRequiredMixin, UserPassesTestMixin) for chat/document operations
- Function-based views for simple pages (index, features, etc.)
- AJAX endpoints return JsonResponse
- File uploads handled with FileField models
- User authentication via Django's built-in auth system
- Bootstrap 5 for frontend styling
- Interview system prompts are in views.py as textwrap.dedent() strings

### Working with the Chat System
The Chat model is central to the application:
- Stores messages as JSON field
- Has key_questions as JSON field (10 timed questions per interview)
- Links to UploadedResume and UploadedJobListing via ForeignKey
- System prompts generated dynamically in views.py based on resume/job listing/difficulty/type
- OpenAI client initialized at module level in views.py

### Database Migrations
Always run migrations after model changes:
```bash
cd active_interview_backend
python3 manage.py makemigrations
python3 manage.py migrate
```

### Static Files
If you modify CSS, JavaScript, or images:
1. Delete `active_interview_backend/staticfiles/` directory
2. Run `python3 manage.py collectstatic --noinput`
3. Restart server/container

## Docker Environment

### When to Use Docker
- For running full integration tests
- Testing production-like environment
- When tests require Nginx or full stack

### Docker Commands
```bash
# Start development environment
docker-compose up -d --build

# Start production environment
docker-compose -f docker-compose.prod.yml up -d --build

# Execute commands in container
docker exec django python3 manage.py test
docker exec django coverage run manage.py test

# View logs
docker logs django
docker logs nginx

# Stop and clean
docker-compose down --volumes --remove-orphans
```

### Cleaning/Restarting
```bash
# Clean Docker environment
docker-compose down --volumes --remove-orphans
docker system prune --all --volumes
sudo systemctl restart docker

# Clean git-tracked files (preserves .env and db/)
git clean -fdx -e .env -e active_interview_backend/db

# Automated clean restart (Linux/Mac only - commits code first!)
sudo ./scripts/clean-restart.sh
```

## CI/CD

### Continuous Integration (GitHub Actions)

**CI.yml** - Runs on all pushes/PRs:
1. **Lint**: Python (flake8) and Django templates (djlint)
2. **Security**: Dependency scanning (safety) and code analysis (bandit)
3. **Test**: Django tests with coverage (80% minimum required)
   - Builds production Docker containers
   - Installs Chrome/Chromedriver for E2E Selenium tests
   - Generates and validates coverage reports
4. **AI Review**: OpenAI-powered code review of git diff
5. **Cleanup**: Archives essential reports (coverage, security, AI review) for 30 days

### Continuous Deployment (Railway)

**CD.yml** - Deploys to Railway on push to `main` or `prod`:
- Uses Railway CLI to trigger deployment
- Runs independently or can be configured to wait for CI
- Requires GitHub secrets:
  - `RAILWAY_TOKEN`: Railway API token (from Railway dashboard → Account Settings → Tokens)
  - `RAILWAY_SERVICE_ID`: Service ID from Railway (found in service settings)

**Railway Configuration** (via Railway dashboard):
- Environment variables: DJANGO_SECRET_KEY, OPENAI_API_KEY, DATABASE_URL, PROD=true
- Build/start commands: Auto-detected for Django
- Domain settings and SSL certificates

### Linting
```bash
# Python linting
flake8 --config active_interview_backend/.flake8 .

# Template linting
djlint --configuration active_interview_backend/djlint.toml active_interview_backend/active_interview_app/templates/ --lint
```

## Common Commands

### Django Management
```bash
# Navigate to backend first
cd active_interview_backend

# Database migrations
python3 manage.py makemigrations
python3 manage.py migrate

# Collect static files (required after CSS/image changes)
python3 manage.py collectstatic --noinput

# Create superuser
python3 manage.py createsuperuser

# Run development server
python3 manage.py runserver
```

## Error Handling

If you encounter errors:
1. **Test failures**: Read the full traceback, identify the failing assertion, fix root cause
2. **Import errors**: Check requirements.txt, verify file structure
3. **Migration errors**: Check for conflicting migrations, try `--merge` if needed
4. **Docker errors**: Check logs with `docker logs django`, verify .env file exists
5. **Coverage failures**: Write tests for uncovered code, check .coveragerc for exclusions

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
Successfully implemented user profile export feature.

Files changed:
- active_interview_backend/active_interview_app/views.py:456 - Added ProfileExportView
- active_interview_backend/active_interview_app/urls.py:34 - Added /profile/export/ route
- active_interview_backend/active_interview_app/tests/test_profile.py:89 - Added test_profile_export

Tests: All passed (45 tests). Coverage: 84% (above 80% requirement).
Linting: No flake8 or djlint errors.

Verification: Tested export functionality manually and with automated test.
```

### Poor Report Example
```
I made some changes to the views file and added stuff. It might work but I'm not sure. There were some errors but I tried to fix them.
```

## Key Technologies
- **Backend**: Django 4.2.19, Django REST Framework
- **Server**: Gunicorn (3 workers in production)
- **Web Server**: Nginx (reverse proxy, static file serving)
- **AI**: OpenAI GPT-4o
- **Frontend**: Bootstrap 5, jQuery, Ajax, DOMPurify
- **File Processing**: PyMuPDF, python-docx, filetype
- **Testing**: Django TestCase, Selenium, Coverage.py, Behave/pytest-bdd
- **Deployment**: Docker Compose, Digital Ocean

## Production Notes
- Production uses `docker-compose.prod.yml` with `PROD=true`
- SSL certificates mounted from host at `/etc/letsencrypt`
- Nginx config: `nginx.prod.conf` (prod) vs `nginx.local.conf` (dev)
- Static files collected to shared volume between Django and Nginx
- Allowed hosts include: `app.activeinterviewservice.me`, localhost, 127.0.0.1
- CSRF trusted origins: `https://app.activeinterviewservice.me`

## Security Considerations
- Never commit secrets or API keys
- Use environment variables for sensitive data
- Validate user input in forms
- Use Django's built-in CSRF protection

## Performance Notes
- OpenAI API calls are expensive - avoid unnecessary calls during testing
- Consider using test fixtures or mocks for AI functionality in tests
- Database is SQLite - suitable for development but be aware of limitations

## Getting Unstuck

If you're stuck:
1. Review this file for architecture overview
2. Search for similar existing functionality (e.g., grep for similar view patterns)
3. Check Django documentation for framework-specific questions
4. Look at test files to understand expected behavior
5. Use Glob to find relevant files, Grep to find code patterns
6. Read the full context of files, not just snippets
