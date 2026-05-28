"""
Data migration: configura el registro Site (django.contrib.sites) segun el entorno.

Ruta sugerida: usuarios/migrations/0002_set_site_domain.py

Ajusta el numero del archivo (0002) al ultimo numero de migracion
que ya exista en usuarios/migrations/. Si el ultimo es 0003_algo.py,
este debe llamarse 0004_set_site_domain.py.

Se ejecuta automaticamente con 'python manage.py migrate', incluyendo
el deploy en Render, sin necesidad de acceso a shell.
"""

from django.conf import settings
from django.db import migrations


def set_site_domain(apps, schema_editor):
    """
    Crea o actualiza el Site con id=1 segun el entorno activo.

    - DEBUG=True  (desarrollo local):   localhost:8000
    - DEBUG=False (produccion, Render): gastu.onrender.com
    """
    Site = apps.get_model('sites', 'Site')

    if settings.DEBUG:
        domain = 'localhost:8000'
        name   = 'GastuApp Dev'
    else:
        domain = 'gastu.onrender.com'
        name   = 'GastuApp'

    Site.objects.update_or_create(
        id=1,
        defaults={'domain': domain, 'name': name},
    )


def undo_site_domain(apps, schema_editor):
    """
    Revierte el Site al valor por defecto de Django.
    Solo se usa si se hace rollback de esta migracion.
    """
    Site = apps.get_model('sites', 'Site')
    Site.objects.filter(id=1).update(
        domain='example.com',
        name='example.com',
    )


class Migration(migrations.Migration):
    """
    Dependencias:
    - usuarios: ultima migracion existente en la app (ajustar el numero)
    - sites:    0001_initial (migracion base de django.contrib.sites)
    """

    dependencies = [
        ('usuarios', '0001_initial'),        # cambiar 0001_initial al nombre real
        ('sites',    '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            set_site_domain,
            reverse_code=undo_site_domain,
        ),
    ]