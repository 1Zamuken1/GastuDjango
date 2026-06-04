from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Presupuesto


@receiver(post_save, sender=Presupuesto)
def auditar_presupuesto_guardar(sender, instance, **kwargs):
    from historial.models import AccionHistorial

    es_creacion = kwargs.get('created', False)
    accion_tipo = AccionHistorial.AccionChoices.CREACION if es_creacion else AccionHistorial.AccionChoices.EDICION
    verbo = "creó" if es_creacion else "editó"

    desc = f"Se {verbo} un presupuesto para la categoría '{instance.categoria.nombre}'"
    if instance.limite:
        desc += f" con límite ${instance.limite}"

    AccionHistorial.objects.create(
        usuario=instance.usuario,
        accion=accion_tipo,
        modulo=AccionHistorial.ModuloChoices.PRESUPUESTOS,
        descripcion=desc,
        referencia_id=str(instance.id),
        monto_afectado=instance.limite,
    )


@receiver(post_delete, sender=Presupuesto)
def auditar_presupuesto_eliminar(sender, instance, **kwargs):
    from historial.models import AccionHistorial

    desc = f"Se eliminó un presupuesto de la categoría '{instance.categoria.nombre}'"

    AccionHistorial.objects.create(
        usuario=instance.usuario,
        accion=AccionHistorial.AccionChoices.ELIMINACION,
        modulo=AccionHistorial.ModuloChoices.PRESUPUESTOS,
        descripcion=desc,
        referencia_id=str(instance.id),
        monto_afectado=instance.limite,
    )
