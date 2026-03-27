"""
Signals de la app de notificaciones.

Escucha el evento post_save del modelo Movimiento y dispara el análisis
de alertas de forma automática cada vez que se crea o edita un movimiento.

Para activar estos signals debes importar este módulo desde el AppConfig
de tu app de notificaciones:

    # notificaciones/apps.py
    from django.apps import AppConfig

    class NotificacionesConfig(AppConfig):
        name = 'notificaciones'

        def ready(self):
            import notificaciones.signals  # noqa: F401
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='movimientos.Movimiento')
def on_movimiento_guardado(sender, instance, created, **kwargs):
    """
    Se ejecuta cada vez que se crea o edita un Movimiento.
    Llama al analizador de alertas de forma segura (nunca falla silenciosamente).
    """
    from .services import analizar_movimiento

    try:
        analizar_movimiento(
            usuario=instance.usuario,
            movimiento=instance,
        )
    except Exception as e:
        # Nunca dejar que un error en las alertas rompa la operación principal
        print(f'[notificaciones] Error al analizar movimiento #{instance.pk}: {e}')