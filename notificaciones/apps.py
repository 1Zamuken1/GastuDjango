from django.apps import AppConfig
 
 
class NotificacionesConfig(AppConfig):
    name = 'notificaciones'
 
    def ready(self):
        import notificaciones.signals  # noqa: F401 — registra los signals al arrancar
 

# from django.apps import AppConfig


# class NotificacionesConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'notificaciones'
