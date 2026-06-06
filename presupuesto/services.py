from decimal import Decimal

from django.db.models import OuterRef, Subquery, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone

from movimientos.models import Movimiento
from .models import Presupuesto


def _qs_con_total_gastado(qs):
    """Annota cada presupuesto con el total gastado en su rango de fechas en 1 subquery.

    Usa un Subquery correlacionado para evitar N+1 al calcular el gasto
    de múltiples presupuestos a la vez. El valor queda disponible como
    `presupuesto._total_gastado`.
    """
    return qs.select_related('categoria').annotate(
        _total_gastado=Coalesce(
            Subquery(
                Movimiento.objects.filter(
                    usuario=OuterRef('usuario'),
                    categoria=OuterRef('categoria'),
                    tipo='EGRESO',
                    fecha_registro__date__gte=OuterRef('fecha_inicio'),
                    fecha_registro__date__lte=OuterRef('fecha_fin'),
                ).values('categoria').annotate(
                    total=Sum('monto')
                ).values('total')[:1],
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
    )


def desactivar_presupuestos_vencidos(usuario):
    """Desactiva todos los presupuestos cuya fecha_fin ya pasó. Retorna los desactivados."""
    hoy = timezone.now().date()
    vencidos = Presupuesto.objects.filter(
        usuario=usuario,
        isActivo=True,
        fecha_fin__lt=hoy
    )
    desactivados = list(vencidos.values('id', 'fecha_fin', 'categoria__nombre'))
    vencidos.update(isActivo=False)
    return desactivados


def calcular_alerta_presupuesto(presupuesto):
    """Calcula el total gastado y porcentaje respecto al límite para un presupuesto.

    Si el presupuesto ya tiene el atributo ``_total_gastado`` (ej: vía
    ``_qs_con_total_gastado``) lo reusa; de lo contrario hace una consulta SUM.
    """
    total_gastado = getattr(presupuesto, '_total_gastado', None)
    if total_gastado is None:
        total_gastado = Movimiento.objects.filter(
            usuario=presupuesto.usuario,
            categoria=presupuesto.categoria,
            tipo='EGRESO',
            fecha_registro__date__range=(
                presupuesto.fecha_inicio,
                presupuesto.fecha_fin
            )
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    limite = presupuesto.limite
    porcentaje = (total_gastado / limite) * 100 if limite > 0 else 0
    return total_gastado, porcentaje


def nivel_alerta(porcentaje):
    """Clasifica un porcentaje de consumo en un nivel de alerta textual.

    Los niveles van desde ``baja`` (< 50 %), pasando por ``nivel_50`` …
    ``nivel_95`` (cada 5 %), hasta ``critica`` (>= 100 %).
    """
    if porcentaje >= 100:
        return "critica"
    if porcentaje >= 50:
        return f"nivel_{(int(porcentaje) // 5) * 5}"
    return "baja"


def obtener_estado_presupuesto(presupuesto):
    """Arma el dict de estado completo (gastado, porcentaje, alerta) para un presupuesto."""
    total_gastado, porcentaje = calcular_alerta_presupuesto(presupuesto)
    alerta = nivel_alerta(porcentaje)
    return {
        "id": presupuesto.id,
        "categoria": presupuesto.categoria.nombre,
        "categoria_id": presupuesto.categoria.id,
        "limite": float(presupuesto.limite),
        "gastado": float(total_gastado),
        "disponible": float(presupuesto.limite - total_gastado),
        "porcentaje": round(float(porcentaje), 2),
        "alerta": alerta,
    }


def obtener_estados_presupuestos(usuario):
    """Retorna todos los presupuestos activos con su alerta en 1 sola consulta SQL."""
    presupuestos = _qs_con_total_gastado(
        Presupuesto.objects.filter(usuario=usuario, isActivo=True)
    )
    return [obtener_estado_presupuesto(p) for p in presupuestos]