from decimal import Decimal
from django.db.models import Sum
from movimientos.models import Movimiento


def actualizar_resumen(usuario, mes, anio):
    """
    Calcula y actualiza el ResumenMensual de un usuario para un mes dado.
    Se llama automáticamente desde los signals de Movimiento.

    Args:
        usuario: instancia del usuario autenticado.
        mes (int): mes a recalcular (1-12).
        anio (int): año a recalcular.
    """
    from .models import ResumenMensual

    # Totales del mes actual
    movimientos_mes = Movimiento.objects.filter(
        usuario=usuario,
        fecha_registro__month=mes,
        fecha_registro__year=anio,
        activo=True
    )

    total_ingresos = movimientos_mes.filter(
        tipo='INGRESO'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    total_egresos = movimientos_mes.filter(
        tipo='EGRESO'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    ingreso_neto = total_ingresos - total_egresos

    # Ahorros del mes — cuando ahorros esté implementado se conecta aquí
    total_ahorros = Decimal('0')

    # Disponible = ingresos - egresos - ahorros
    disponible = ingreso_neto - total_ahorros

    # Acumulados históricos — suma de todos los ingresos netos anteriores
    resumenes_anteriores = ResumenMensual.objects.filter(
        usuario=usuario
    ).exclude(mes=mes, anio=anio)

    ganancia_acumulada = resumenes_anteriores.aggregate(
        total=Sum('ingreso_neto')
    )['total'] or Decimal('0')
    ganancia_acumulada += ingreso_neto

    ahorro_total = resumenes_anteriores.aggregate(
        total=Sum('total_ahorros')
    )['total'] or Decimal('0')
    ahorro_total += total_ahorros

    # Crear o actualizar el resumen del mes
    ResumenMensual.objects.update_or_create(
        usuario=usuario,
        mes=mes,
        anio=anio,
        defaults={
            'total_ingresos': total_ingresos,
            'total_egresos': total_egresos,
            'total_ahorros': total_ahorros,
            'ingreso_neto': ingreso_neto,
            'disponible': disponible,
            'ganancia_acumulada': ganancia_acumulada,
            'ahorro_total': ahorro_total,
        }
    )