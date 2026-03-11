import json
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.shortcuts import render

from dashboard.models import ResumenMensual
from movimientos.models import Movimiento
from notificaciones.models import Notificacion


MESES_ES = {
    1: 'Enero',   2: 'Febrero',   3: 'Marzo',    4: 'Abril',
    5: 'Mayo',    6: 'Junio',     7: 'Julio',     8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}

ZERO = Decimal('0')


def _mes_anterior(mes, anio, n):
    """Retorna (mes, anio) retrocediendo n meses."""
    mes_total = mes - n
    if mes_total <= 0:
        anios_atras   = (-mes_total // 12) + 1
        mes_resultado  = mes_total + anios_atras * 12
        anio_resultado = anio - anios_atras
    else:
        mes_resultado  = mes_total
        anio_resultado = anio
    return mes_resultado, anio_resultado


def _totales_desde_movimientos(user, mes, anio):
    """
    Fallback: calcula ingresos y egresos del mes directamente
    desde Movimiento cuando ResumenMensual no tiene datos aún
    (ocurre si las signals están duplicadas o no se han disparado).
    """
    qs = Movimiento.objects.filter(
        usuario=user,
        activo=True,
        fecha_registro__month=mes,
        fecha_registro__year=anio,
    )
    ingresos = qs.filter(tipo='INGRESO').aggregate(t=Sum('monto'))['t'] or ZERO
    egresos  = qs.filter(tipo='EGRESO').aggregate(t=Sum('monto'))['t'] or ZERO
    return ingresos, egresos


@login_required
def home_view(request):
    """
    Vista principal del dashboard.
    Prioriza ResumenMensual; si no hay datos, consulta Movimiento directamente.
    """
    hoy  = date.today()
    mes  = hoy.month
    anio = hoy.year
    user = request.user

    # ── Resumen del mes actual ────────────────────────────────────────────────
    resumen = ResumenMensual.objects.filter(
        usuario=user, mes=mes, anio=anio,
    ).first()

    if resumen and (resumen.total_ingresos or resumen.total_egresos):
        total_ingresos = resumen.total_ingresos
        total_egresos  = resumen.total_egresos
        hay_deficit    = bool(resumen.deficit)
    else:
        # Fallback directo a Movimiento
        total_ingresos, total_egresos = _totales_desde_movimientos(user, mes, anio)
        hay_deficit = total_egresos > total_ingresos

    total_ahorros = ZERO  # placeholder hasta módulo ahorros

    # ── Cards calculadas ──────────────────────────────────────────────────────
    diferencia = total_ingresos - total_egresos
    utilidad   = total_ingresos - total_egresos - total_ahorros
    ahorro_total = ZERO

    # Disponible: suma de ingreso_neto de ResumenMensual anteriores + diferencia actual
    acumulado_anterior = ResumenMensual.objects.filter(
        usuario=user,
    ).exclude(mes=mes, anio=anio).aggregate(t=Sum('ingreso_neto'))['t'] or ZERO

    # Si el ResumenMensual pasado también es vacío, sumar balances mes a mes desde Movimiento
    if not acumulado_anterior:
        for i in range(1, 13):     # máximo 12 meses atrás para el acumulado
            m, a = _mes_anterior(mes, anio, i)
            if a < anio - 2:       # no ir más de 2 años atrás
                break
            ing, egr = _totales_desde_movimientos(user, m, a)
            acumulado_anterior += (ing - egr)

    disponible = acumulado_anterior + diferencia

    # ── Histórico 6 meses — stacked bar ──────────────────────────────────────
    labels_h   = []
    ingresos_h = []
    egresos_h  = []
    ahorros_h  = []

    for i in range(5, -1, -1):
        m, a = _mes_anterior(mes, anio, i)
        r = ResumenMensual.objects.filter(usuario=user, mes=m, anio=a).first()

        if r and (r.total_ingresos or r.total_egresos):
            ing = float(r.total_ingresos)
            egr = float(r.total_egresos)
        else:
            # Fallback por mes
            _ing, _egr = _totales_desde_movimientos(user, m, a)
            ing = float(_ing)
            egr = float(_egr)

        labels_h.append(f"{MESES_ES[m][:3]} {str(a)[2:]}")
        ingresos_h.append(ing)
        egresos_h.append(egr)
        ahorros_h.append(0)

    historico_json = json.dumps({
        'labels':   labels_h,
        'ingresos': ingresos_h,
        'egresos':  egresos_h,
        'ahorros':  ahorros_h,
    })

    # ── Pie chart — egresos por categoría del mes ─────────────────────────────
    egresos_cat = (
        Movimiento.objects
        .filter(
            usuario=user,
            tipo='EGRESO',
            activo=True,
            fecha_registro__month=mes,
            fecha_registro__year=anio,
        )
        .values('categoria__nombre')
        .annotate(total=Sum('monto'))
        .order_by('-total')[:8]
    )

    pie_colores = [
        '#f97316', '#f87171', '#fbbf24', '#a3e635',
        '#34d399', '#38bdf8', '#818cf8', '#f472b6',
    ]
    pie_labels  = [item['categoria__nombre'] or 'Sin categoría' for item in egresos_cat]
    pie_valores = [float(item['total']) for item in egresos_cat]

    pie_json = json.dumps({
        'labels':  pie_labels,
        'valores': pie_valores,
        'colores': pie_colores[:len(pie_labels)],
    })

    # ── Últimos movimientos ───────────────────────────────────────────────────
    ultimos_movimientos = (
        Movimiento.objects
        .filter(usuario=user, activo=True)
        .select_related('categoria')
        .order_by('-fecha_registro')[:6]
    )

    # ── Notificaciones ────────────────────────────────────────────────────────
    notificaciones_count = Notificacion.objects.filter(
        usuario=user, leida=False,
    ).count()

    ultimas_notificaciones = (
        Notificacion.objects
        .filter(usuario=user)
        .order_by('-fecha_creacion')[:4]
    )

    context = {
        # Cards
        'total_ingresos': total_ingresos,
        'utilidad':       utilidad,
        'total_egresos':  total_egresos,
        'total_ahorros':  total_ahorros,
        'disponible':     disponible,
        'diferencia':     diferencia,
        'ahorro_total':   ahorro_total,
        'hay_deficit':    hay_deficit,
        # Gráficos
        'historico_json': historico_json,
        'pie_json':       pie_json,
        # Tabla
        'ultimos_movimientos': ultimos_movimientos,
        # Notificaciones
        'notificaciones_count':   notificaciones_count,
        'ultimas_notificaciones': ultimas_notificaciones,
        # Metadata
        'mes_nombre': MESES_ES[mes],
        'anio':       anio,
        'hoy':        hoy,
    }

    return render(request, 'dashboard/home.html', context)