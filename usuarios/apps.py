from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    """Configuración de la app de usuarios."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usuarios'

    def ready(self):
        """Registra los signals al iniciar la app."""
        import usuarios.signals