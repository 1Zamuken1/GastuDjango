from django.apps import AppConfig
 
 
class NotificacionesConfig(AppConfig):
    name = 'notificaciones'
 
    def ready(self):
        import notificaciones.signals  # noqa: F401 — registra los signals al arrancar
