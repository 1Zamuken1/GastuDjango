from django.db.models import Sum
from decimal import Decimal
from movimientos.models import Movimiento


def calcular_alerta_presupuesto(presupuesto):
    total_gastado = (
        Movimiento.objects.filter(
            usuario=presupuesto.usuario,
            categoria=presupuesto.categoria,
            tipo='EGRESO',
            fecha_registro__date__range=(
                presupuesto.fecha_inicio,
                presupuesto.fecha_fin
            )
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
    )

    limite = presupuesto.limite
    porcentaje = (total_gastado / limite) * 100 if limite > 0 else 0

    return total_gastado, porcentaje


def nivel_alerta(porcentaje):
    if porcentaje >= 100:
        return "critica"
    elif porcentaje >= 80:
        return "alta"
    elif porcentaje >= 50:
        return "media"
    else:
        return "baja"


def obtener_estado_presupuesto(presupuesto):
    total_gastado, porcentaje = calcular_alerta_presupuesto(presupuesto)
    alerta = nivel_alerta(porcentaje)

    return {
        "categoria": presupuesto.categoria.nombre,
        "limite": float(presupuesto.limite),
        "gastado": float(total_gastado),
        "porcentaje": round(float(porcentaje), 2),
        "alerta": alerta
    }