from django.db import migrations


def crear_admin(apps, schema_editor):
    from usuarios.models import Usuario
    if not Usuario.objects.filter(username='admin').exists():
        Usuario.objects.create_superuser(
            username='admin',
            email='admin@gastuapp.com',
            password='Admin123!',
            rol='ADMIN'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0002_preferencias'),
    ]

    operations = [
        migrations.RunPython(crear_admin, migrations.RunPython.noop),
    ]