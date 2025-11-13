#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Remove test files from production deployment (security & size optimization)
echo "Removing test files from production..."
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "test_*.py" -delete 2>/dev/null || true
find . -type f -name "*_test.py" -delete 2>/dev/null || true
rm -rf .pytest_cache/ pytest.ini .coverage htmlcov/ coverage.xml 2>/dev/null || true
rm -rf features/ AI_code_reviews/ 2>/dev/null || true
echo "Test files removed."

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

