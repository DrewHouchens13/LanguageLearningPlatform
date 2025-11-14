#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# ===================================================================
# CRITICAL SECURITY: Remove ALL test files from production deployment
# ===================================================================
# Test files contain sensitive data, test credentials, and expose
# internal system behavior. They must NEVER reach production.
#
# Defense in depth: This is the LAST LINE OF DEFENSE. Test files
# should ideally be excluded via .gitignore, but this ensures they
# are removed even if accidentally committed.
# ===================================================================

echo "========================================="
echo "SECURITY: Removing test files from production..."
echo "========================================="

# Remove test directories (home/tests/, features/, etc.)
echo "Removing test directories..."
rm -rf home/tests/ 2>/dev/null || true
rm -rf features/ 2>/dev/null || true
rm -rf AI_code_reviews/ 2>/dev/null || true
rm -rf local_testing/ 2>/dev/null || true

# Remove individual test files (test_*.py, *_test.py)
echo "Removing individual test files..."
find . -type f -name "test_*.py" -delete 2>/dev/null || true
find . -type f -name "*_test.py" -delete 2>/dev/null || true

# Remove pytest configuration and cache
echo "Removing pytest artifacts..."
rm -rf .pytest_cache/ 2>/dev/null || true
rm -f pytest.ini 2>/dev/null || true
rm -f .coverage 2>/dev/null || true
rm -rf htmlcov/ 2>/dev/null || true
rm -f coverage.xml 2>/dev/null || true

# Remove BDD/Gherkin feature files
echo "Removing BDD feature files..."
find . -type f -name "*.feature" -delete 2>/dev/null || true

# Remove testing configuration files
echo "Removing test configuration files..."
rm -f .coveragerc 2>/dev/null || true
rm -f tox.ini 2>/dev/null || true
rm -f .bandit 2>/dev/null || true
rm -f pylint_output.txt 2>/dev/null || true

# Remove __pycache__ directories
echo "Removing __pycache__ directories..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Remove any remaining step_defs (BDD test implementations)
echo "Removing step definition files..."
rm -rf step_defs/ 2>/dev/null || true

# Remove documentation files (security risk, not needed in production)
echo "Removing documentation files..."
find . -type f -name "*.md" ! -path "./venv/*" -delete 2>/dev/null || true
rm -f README.md CLAUDE.md SESSION_PROGRESS.md PRODUCTION_SECURITY.md 2>/dev/null || true
rm -f SPRINT*.md STYLE_GUIDE.md AI_CODE_REVIEW_LOG.md 2>/dev/null || true
rm -f .gitignore .pylintrc .bandit .coveragerc 2>/dev/null || true
rm -rf .github/ 2>/dev/null || true

# Security verification - Check if any test files remain
echo "========================================="
echo "SECURITY VERIFICATION: Checking for remaining test files..."
REMAINING_TESTS=$(find . -name "test_*.py" -o -name "*_test.py" -o -name "*.feature" | wc -l)
if [ "$REMAINING_TESTS" -gt 0 ]; then
    echo "WARNING: $REMAINING_TESTS test files still present after cleanup!"
    find . -name "test_*.py" -o -name "*_test.py" -o -name "*.feature"
else
    echo "SUCCESS: All test files removed from production deployment."
fi

# Verify documentation files removed
REMAINING_DOCS=$(find . -type f -name "*.md" ! -path "./venv/*" | wc -l)
if [ "$REMAINING_DOCS" -gt 0 ]; then
    echo "WARNING: $REMAINING_DOCS documentation files still present!"
    find . -type f -name "*.md" ! -path "./venv/*"
else
    echo "SUCCESS: All documentation files removed from production deployment."
fi
echo "========================================="

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate

# Load onboarding questions fixtures
python manage.py loaddata home/fixtures/onboarding_spanish.json

# Create shapes lesson with flashcards and quiz
python manage.py create_shapes_lesson

# Create colors lesson with flashcards and quiz
python manage.py create_colors_lesson

