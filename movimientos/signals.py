from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Movimiento


@receiver(post_save, sender=Movimiento)
def actualizar_resumen_al_guardar(sender, instance, **kwargs):
    """
    Recalcula ResumenMensual y genera notificaciones
    cuando se crea o edita un Movimiento.
    """
    from dashboard.services import actualizar_resumen
    from notificaciones.services import analizar_movimiento

    actualizar_resumen(
        usuario=instance.usuario,
        mes=instance.fecha_registro.month,
        anio=instance.fecha_registro.year,
    )
    analizar_movimiento(
        usuario=instance.usuario,
        movimiento=instance,
    )


@receiver(post_delete, sender=Movimiento)
def actualizar_resumen_al_eliminar(sender, instance, **kwargs):
    """
    Recalcula ResumenMensual cuando se elimina un Movimiento.
    No dispara notificación en eliminación.
    """
    from dashboard.services import actualizar_resumen

    actualizar_resumen(
        usuario=instance.usuario,
        mes=instance.fecha_registro.month,
        anio=instance.fecha_registro.year,
    )