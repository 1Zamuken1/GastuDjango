from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CategoriasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'categorias'

    def ready(self):
        from django.core.management import call_command

        def cargar_datos(sender, **kwargs):
            try:
                call_command('loaddata', 'semilla.json')
            except Exception as e:
                print(f"Error cargando semilla: {e}")

        post_migrate.connect(cargar_datos, sender=self)