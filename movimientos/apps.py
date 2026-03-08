from django.apps import AppConfig


class MovimientosConfig(AppConfig):
    """Configuración de la app de movimientos."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'movimientos'

    def ready(self):
        """Registra los signals al iniciar la app."""
        import movimientos.signals