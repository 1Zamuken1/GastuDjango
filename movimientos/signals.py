from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Movimiento


@receiver(post_save, sender=Movimiento)
def actualizar_resumen_al_guardar(sender, instance, **kwargs):
    """
    Recalcula el ResumenMensual cuando se crea o edita un Movimiento.

    Args:
        instance: instancia del Movimiento guardado.
    """
    from dashboard.services import actualizar_resumen
    actualizar_resumen(
        usuario=instance.usuario,
        mes=instance.fecha_registro.month,
        anio=instance.fecha_registro.year
    )


@receiver(post_delete, sender=Movimiento)
def actualizar_resumen_al_eliminar(sender, instance, **kwargs):
    """
    Recalcula el ResumenMensual cuando se elimina un Movimiento.

    Args:
        instance: instancia del Movimiento eliminado.
    """
    from dashboard.services import actualizar_resumen
    actualizar_resumen(
        usuario=instance.usuario,
        mes=instance.fecha_registro.month,
        anio=instance.fecha_registro.year
    )
    
# Notificaciones
@receiver(post_save, sender=Movimiento)
def actualizar_resumen_al_guardar(sender, instance, **kwargs):
    """
    Recalcula el ResumenMensual y analiza notificaciones
    cuando se crea o edita un Movimiento.

    Args:
        instance: instancia del Movimiento guardado.
    """
    from dashboard.services import actualizar_resumen
    from notificaciones.services import analizar_movimiento
    from decimal import Decimal

    actualizar_resumen(
        usuario=instance.usuario,
        mes=instance.fecha_registro.month,
        anio=instance.fecha_registro.year
    )
    analizar_movimiento(
        usuario=instance.usuario,
        mes=instance.fecha_registro.month,
        anio=instance.fecha_registro.year,
        ultimo_egreso=instance.monto if instance.tipo == 'EGRESO' else None
    )


@receiver(post_delete, sender=Movimiento)
def actualizar_resumen_al_eliminar(sender, instance, **kwargs):
    """
    Recalcula el ResumenMensual y analiza notificaciones
    cuando se elimina un Movimiento.

    Args:
        instance: instancia del Movimiento eliminado.
    """
    from dashboard.services import actualizar_resumen
    from notificaciones.services import analizar_movimiento

    actualizar_resumen(
        usuario=instance.usuario,
        mes=instance.fecha_registro.month,
        anio=instance.fecha_registro.year
    )
    analizar_movimiento(
        usuario=instance.usuario,
        mes=instance.fecha_registro.month,
        anio=instance.fecha_registro.year
    )