"""Crea el superusuario si no existe ninguno."""
import os
from django.contrib.auth import get_user_model

User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
    email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@gastuapp.com")
    password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "Admin123!")
    User.objects.create_superuser(username=username, email=email, password=password)
    print("Superuser created successfully")
else:
    print("Superuser already exists, skipping")
