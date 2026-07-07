#!/usr/bin/env bash
# exit on error
set -o errexit

echo "=== Installing dependencies ==="
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --no-input

echo "=== Running database migrations ==="
python manage.py migrate

echo "=== Creating superuser (if not exists) ==="
python manage.py shell -c "
from django.contrib.auth import get_user_model
import os
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
    email    = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@gastuapp.com')
    password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'Admin123!')
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superuser \"{username}\" created successfully')
else:
    print('Superuser already exists, skipping')
"
