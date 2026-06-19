from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(post_save, sender='ahorros.AhorroMeta')
def historial_ahorro_guardado(sender, instance, created, update_fields=None, **kwargs):
    """Registra en el historial la creación o edición de una meta de ahorro."""
    if not created and update_fields is not None:
        return
        
    from historial.models import AccionHistorial

    accion = (
        AccionHistorial.AccionChoices.CREACION
        if created
        else AccionHistorial.AccionChoices.EDICION
    )
    verbo = "creó" if created else "editó"
    categoria_nombre = instance.categoria.nombre if instance.categoria_id else "sin categoría"

    AccionHistorial.objects.create(
        usuario=instance.usuario,
        accion=accion,
        modulo=AccionHistorial.ModuloChoices.AHORROS,
        descripcion=(
            f"Se {verbo} la meta '{categoria_nombre}'"
            f"{' — ' + instance.descripcion if instance.descripcion else ''}"
        ),
        referencia_id=str(instance.id),
        monto_afectado=instance.monto_meta,
    )


@receiver(post_delete, sender='ahorros.AhorroMeta')
def historial_ahorro_eliminado(sender, instance, **kwargs):
    """
    Registra en el historial la eliminacion de una meta de ahorro.

    views.py llama primero a AporteAhorro.objects.filter(ahorro=ahorro).delete()
    (bulk delete — no dispara post_delete de AporteAhorro) y luego ahorro.delete()
    que si dispara este signal. Por eso el registro de historial de la meta
    queda limpio y sin duplicados de cuotas.
    """
    from historial.models import AccionHistorial

    categoria_nombre = instance.categoria.nombre if instance.categoria_id else "sin categoria"
    total_acumulado = instance.total_acumulado or 0

    if total_acumulado > 0:
        descripcion = (
            f"Se elimino la meta '{categoria_nombre}'"
            f"{' -- ' + instance.descripcion if instance.descripcion else ''}."
            f" Tu aportado en esta meta (${total_acumulado:,.0f})"
            f" ya se encuentra en disponible"
        )
    else:
        descripcion = (
            f"Se elimino la meta '{categoria_nombre}'"
            f"{' -- ' + instance.descripcion if instance.descripcion else ''}"
        )

    AccionHistorial.objects.create(
        usuario=instance.usuario,
        accion=AccionHistorial.AccionChoices.ELIMINACION,
        modulo=AccionHistorial.ModuloChoices.AHORROS,
        descripcion=descripcion,
        referencia_id=str(instance.id),
        monto_afectado=instance.monto_meta,
    )


@receiver(post_save, sender='ahorros.AporteAhorro')
def historial_aporte_registrado(sender, instance, created, **kwargs):
    """
    Registra en el historial cuando se efectúa un aporte (estado_ap = APORTADO).

    Reglas:
    - bulk_create() en generar_cuotas() NO dispara este signal — seguro.
    - save() individual en registrar_aporte() SÍ lo dispara.
    - Solo auditamos cuando estado_ap == APORTADO para ignorar la creación
      de cuotas pendientes desde generar_cuotas() si alguna vez usa save().
    - created=True con estado APORTADO no ocurre en el flujo actual,
      pero se ignora igualmente para no registrar falsos positivos.

    El usuario se obtiene via instance.ahorro.usuario porque AporteAhorro
    no tiene FK directa a Usuario.
    """
    from historial.models import AccionHistorial

    # Ignorar cuotas que aún no se han pagado
    if instance.estado_ap != 'APORTADO':
        return

    es_extraordinario = getattr(instance, '_es_extraordinario', False)

    # La creación masiva de cuotas (bulk_create) no llega aquí,
    # pero si llegara (created=True) la ignoramos para no contaminar el historial.
    if created and not es_extraordinario:
        return

    categoria_nombre = (
        instance.ahorro.categoria.nombre
        if instance.ahorro_id and instance.ahorro.categoria_id
        else "sin categoría"
    )

    if es_extraordinario:
        descripcion = f"Se registró un aporte extraordinario a la meta '{categoria_nombre}'"
    else:
        descripcion = f"Se registró un aporte a la meta '{categoria_nombre}'"

    AccionHistorial.objects.create(
        usuario=instance.ahorro.usuario,
        accion=AccionHistorial.AccionChoices.CREACION,
        modulo=AccionHistorial.ModuloChoices.AHORROS,
        descripcion=descripcion,
        referencia_id=str(instance.id),
        monto_afectado=instance.aporte,
    )

    # Actualizar resumen mensual e invalidar caché
    from dashboard.services import actualizar_resumen
    actualizar_resumen(
        usuario=instance.ahorro.usuario,
        mes=instance.fecha_registro.month,
        anio=instance.fecha_registro.year
    )

@receiver(post_delete, sender='ahorros.AporteAhorro')
def actualizar_resumen_aporte_eliminado(sender, instance, **kwargs):
    """Actualiza el resumen y limpia la caché al eliminar un aporte."""
    if instance.estado_ap == 'APORTADO':
        from dashboard.services import actualizar_resumen
        actualizar_resumen(
            usuario=instance.ahorro.usuario,
            mes=instance.fecha_registro.month,
            anio=instance.fecha_registro.year
        )
