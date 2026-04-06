from django.db.models import Sum
from decimal import Decimal
from movimientos.models import Movimiento
from .models import Presupuesto
from django.utils import timezone

def desactivar_presupuestos_vencidos(usuario):
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
    elif porcentaje >= 95:
        return "nivel_95"
    elif porcentaje >= 90:
        return "nivel_90"
    elif porcentaje >= 85:
        return "nivel_85"
    elif porcentaje >= 80:
        return "nivel_80"
    elif porcentaje >= 75:
        return "nivel_75"
    elif porcentaje >= 70:
        return "nivel_70"
    elif porcentaje >= 65:
        return "nivel_65"
    elif porcentaje >= 60:
        return "nivel_60"
    elif porcentaje >= 55:
        return "nivel_55"
    elif porcentaje >= 50:
        return "nivel_50"
    else:
        return "baja"


def obtener_estado_presupuesto(presupuesto):
    total_gastado, porcentaje = calcular_alerta_presupuesto(presupuesto)
    alerta = nivel_alerta(porcentaje)

    return {
            "id": presupuesto.id,
            "categoria": presupuesto.categoria.nombre,
            "categoria_id": presupuesto.categoria.id,
            "limite": float(presupuesto.limite),
            "gastado": float(total_gastado),
            "porcentaje": round(float(porcentaje), 2),
            "alerta": alerta
        }