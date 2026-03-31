from django.apps import AppConfig


class AhorrosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ahorros'

    def ready(self):
        """Conecta los signals al iniciar la app."""
        import ahorros.signals 