from decimal import Decimal
from django.db.models import Sum
from movimientos.models import Movimiento


def actualizar_resumen(usuario, mes, anio):
    """
    Calcula y actualiza el ResumenMensual de un usuario para un mes dado.
    Se llama automáticamente desde los signals de Movimiento.

    Campos almacenados:
    - total_ingresos, total_egresos, total_ahorros : totales del mes
    - ingreso_neto   : ingresos - egresos - ahorros (utilidad mensual)
    - disponible     : igual a ingreso_neto por mes
    - ganancia_acumulada : suma histórica de todos los ingreso_neto hasta este mes
    - ahorro_total   : suma histórica de todos los total_ahorros hasta este mes

    Args:
        usuario: instancia del usuario autenticado.
        mes (int): mes a recalcular (1-12).
        anio (int): año a recalcular.
    """
    from .models import ResumenMensual

    ZERO = Decimal('0')

    # ── Totales del mes actual desde Movimiento ───────────────────────────────
    movimientos_mes = Movimiento.objects.filter(
        usuario=usuario,
        fecha_registro__month=mes,
        fecha_registro__year=anio,
        activo=True,
    )

    total_ingresos = movimientos_mes.filter(tipo='INGRESO').aggregate(
        total=Sum('monto'))['total'] or ZERO
    total_egresos = movimientos_mes.filter(tipo='EGRESO').aggregate(
        total=Sum('monto'))['total'] or ZERO

    total_ahorros = ZERO   # placeholder hasta módulo ahorros

    ingreso_neto = total_ingresos - total_egresos - total_ahorros
    disponible   = ingreso_neto

    # ── Acumulados históricos — todos los meses excepto el actual ─────────────
    anteriores = ResumenMensual.objects.filter(
        usuario=usuario,
    ).exclude(mes=mes, anio=anio)

    ganancia_acumulada = (
        anteriores.aggregate(total=Sum('ingreso_neto'))['total'] or ZERO
    ) + ingreso_neto

    ahorro_total = (
        anteriores.aggregate(total=Sum('total_ahorros'))['total'] or ZERO
    ) + total_ahorros

    # ── Persistir en BD ───────────────────────────────────────────────────────
    ResumenMensual.objects.update_or_create(
        usuario=usuario,
        mes=mes,
        anio=anio,
        defaults={
            'total_ingresos':     total_ingresos,
            'total_egresos':      total_egresos,
            'total_ahorros':      total_ahorros,
            'ingreso_neto':       ingreso_neto,
            'disponible':         disponible,
            'ganancia_acumulada': ganancia_acumulada,
            'ahorro_total':       ahorro_total,
        }
    )