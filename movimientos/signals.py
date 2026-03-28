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

    # Auditar acción
    from historial.models import AccionHistorial
    from decimal import Decimal
    
    es_creacion = kwargs.get('created', False)
    accion_tipo = AccionHistorial.AccionChoices.CREACION if es_creacion else AccionHistorial.AccionChoices.EDICION
    
    tipo_str = "ingreso" if instance.tipo == "INGRESO" else "egreso"
    verbo = "registró" if es_creacion else "editó"
    
    desc = f"Se {verbo} un {tipo_str} en la categoría '{instance.categoria.nombre}'"
    if instance.descripcion:
        desc += f" ({instance.descripcion})"
        
    modulo_tipo = (
        AccionHistorial.ModuloChoices.INGRESOS
        if instance.tipo == 'INGRESO'
        else AccionHistorial.ModuloChoices.EGRESOS
    )

    AccionHistorial.objects.create(
        usuario=instance.usuario,
        accion=accion_tipo,
        modulo=modulo_tipo,
        descripcion=desc,
        referencia_id=str(instance.id),
        monto_afectado=instance.monto
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

    # Auditar acción
    from historial.models import AccionHistorial
    
    tipo_str = "ingreso" if instance.tipo == "INGRESO" else "egreso"
    desc = f"Se eliminó un {tipo_str} de la categoría '{instance.categoria.nombre}'"
    if instance.descripcion:
        desc += f" ({instance.descripcion})"
        
    modulo_tipo = (
        AccionHistorial.ModuloChoices.INGRESOS
        if instance.tipo == 'INGRESO'
        else AccionHistorial.ModuloChoices.EGRESOS
    )

    AccionHistorial.objects.create(
        usuario=instance.usuario,
        accion=AccionHistorial.AccionChoices.ELIMINACION,
        modulo=modulo_tipo,
        descripcion=desc,
        referencia_id=str(instance.id),
        monto_afectado=instance.monto
    )