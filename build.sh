#!/usr/bin/env bash
# exit on error
set -o errexit

echo "=== Installing dependencies ==="
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --no-input

echo "=== Syncing allauth migrations (fake) ==="
python manage.py migrate account --fake
python manage.py migrate socialaccount --fake

echo "=== Running database migrations ==="
python manage.py migrate

echo "=== Ingesting seed data (semilla.json) ==="
python manage.py loaddata semilla.json
