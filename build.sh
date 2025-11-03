#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate

# Load onboarding questions fixtures
python manage.py loaddata home/fixtures/onboarding_spanish.json

# Create shapes lesson with flashcards and quiz
python manage.py create_shapes_lesson

