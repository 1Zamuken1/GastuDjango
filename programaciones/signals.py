from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Programacion


@receiver(post_save, sender=Programacion)
def auditar_programacion_guardar(sender, instance, **kwargs):
    from historial.models import AccionHistorial

    es_creacion = kwargs.get('created', False)
    accion_tipo = AccionHistorial.AccionChoices.CREACION if es_creacion else AccionHistorial.AccionChoices.EDICION
    verbo = "creó" if es_creacion else "editó"
    tipo_str = "ingreso" if instance.tipo == "INGRESO" else "egreso"

    desc = f"Se {verbo} una programación de {tipo_str} en '{instance.categoria.nombre}'"
    if instance.descripcion:
        desc += f" ({instance.descripcion})"

    AccionHistorial.objects.create(
        usuario=instance.usuario,
        accion=accion_tipo,
        modulo=AccionHistorial.ModuloChoices.PROGRAMACIONES,
        descripcion=desc,
        referencia_id=str(instance.id),
        monto_afectado=instance.monto_programado,
    )


@receiver(post_delete, sender=Programacion)
def auditar_programacion_eliminar(sender, instance, **kwargs):
    from historial.models import AccionHistorial

    tipo_str = "ingreso" if instance.tipo == "INGRESO" else "egreso"
    desc = f"Se eliminó una programación de {tipo_str} de la categoría '{instance.categoria.nombre}'"
    if instance.descripcion:
        desc += f" ({instance.descripcion})"

    AccionHistorial.objects.create(
        usuario=instance.usuario,
        accion=AccionHistorial.AccionChoices.ELIMINACION,
        modulo=AccionHistorial.ModuloChoices.PROGRAMACIONES,
        descripcion=desc,
        referencia_id=str(instance.id),
        monto_afectado=instance.monto_programado,
    )
