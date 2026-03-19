import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncDate, TruncWeek
from django.http import JsonResponse
from django.shortcuts import render

from dashboard.models import ResumenMensual
from movimientos.models import Movimiento
from notificaciones.models import Notificacion


MESES_ES = {
    1: 'Enero',   2: 'Febrero',  3: 'Marzo',    4: 'Abril',
    5: 'Mayo',    6: 'Junio',    7: 'Julio',     8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}

ZERO = Decimal('0')


def _mes_anterior(mes, anio, n):
    mes_total = mes - n
    if mes_total <= 0:
        anios_atras    = (-mes_total // 12) + 1
        mes_resultado  = mes_total + anios_atras * 12
        anio_resultado = anio - anios_atras
    else:
        mes_resultado  = mes_total
        anio_resultado = anio
    return mes_resultado, anio_resultado


def _totales_movimiento(user, mes, anio):
    qs = Movimiento.objects.filter(
        usuario=user, activo=True,
        fecha_registro__month=mes,
        fecha_registro__year=anio,
    )
    ingresos = qs.filter(tipo='INGRESO').aggregate(t=Sum('monto'))['t'] or ZERO
    egresos  = qs.filter(tipo='EGRESO').aggregate(t=Sum('monto'))['t'] or ZERO
    return ingresos, egresos


@login_required
def home_view(request):
    hoy  = date.today()
    mes  = hoy.month
    anio = hoy.year
    user = request.user

    resumen = ResumenMensual.objects.filter(
        usuario=user, mes=mes, anio=anio,
    ).first()

    if resumen:
        total_ingresos = resumen.total_ingresos
        total_egresos  = resumen.total_egresos
        total_ahorros  = resumen.total_ahorros
        utilidad       = resumen.ingreso_neto
        disponible     = resumen.ganancia_acumulada
        ahorro_total   = resumen.ahorro_total
        hay_deficit    = resumen.deficit
    else:
        total_ingresos, total_egresos = _totales_movimiento(user, mes, anio)
        total_ahorros = ZERO
        utilidad      = total_ingresos - total_egresos
        disponible    = utilidad
        ahorro_total  = ZERO
        hay_deficit   = total_egresos > total_ingresos

    diferencia = total_ingresos - total_egresos

    # ── Pie chart — egresos por categoría del mes ─────────────────────────────
    egresos_cat = (
        Movimiento.objects
        .filter(
            usuario=user, tipo='EGRESO', activo=True,
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
        .order_by('-fecha_registro')[:10]
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
        'total_ingresos':         total_ingresos,
        'total_egresos':          total_egresos,
        'total_ahorros':          total_ahorros,
        'utilidad':               utilidad,
        'disponible':             disponible,
        'diferencia':             diferencia,
        'ahorro_total':           ahorro_total,
        'hay_deficit':            hay_deficit,
        'pie_json':               pie_json,
        'ultimos_movimientos':    ultimos_movimientos,
        'notificaciones_count':   notificaciones_count,
        'ultimas_notificaciones': ultimas_notificaciones,
        'mes_nombre':             MESES_ES[mes],
        'anio':                   anio,
        'hoy':                    hoy,
    }

    return render(request, 'dashboard/home.html', context)


@login_required
def tendencia_mes(request):
    """
    Endpoint JSON para el gráfico de tendencia del mes actual.

    GET param: granularidad — 'dia' | 'semana'
    Solo muestra datos del mes en curso, sin histórico.

    - dia    : un punto por día del mes, desde el día 1 hasta hoy
    - semana : agrupado por semanas del mes, máx 5 puntos
    """
    hoy          = date.today()
    mes          = hoy.month
    anio         = hoy.year
    user         = request.user
    granularidad = request.GET.get('granularidad', 'dia')
    primer_dia   = date(anio, mes, 1)

    # Queryset base del mes actual — dos queries en total (una por tipo)
    qs_base = Movimiento.objects.filter(
        usuario=user,
        activo=True,
        fecha_registro__month=mes,
        fecha_registro__year=anio,
    )

    if granularidad == 'semana':
        def _semanales(tipo):
            return {
                row['semana'].date(): float(row['total'])
                for row in qs_base
                .filter(tipo=tipo)
                .annotate(semana=TruncWeek('fecha_registro'))
                .values('semana')
                .annotate(total=Sum('monto'))
                .order_by('semana')
            }

        ing_map = _semanales('INGRESO')
        egr_map = _semanales('EGRESO')
        semanas = sorted(set(list(ing_map.keys()) + list(egr_map.keys())))

        # Calcular qué semana del mes es cada fecha
        def _num_semana(d):
            return ((d.day - 1 + primer_dia.weekday()) // 7) + 1

        labels   = [f"Semana {_num_semana(s)}" for s in semanas]
        ingresos = [ing_map.get(s, 0) for s in semanas]
        egresos  = [egr_map.get(s, 0) for s in semanas]

    else:
        # día a día desde el 1 hasta hoy
        def _diarios(tipo):
            return {
                row['fecha']: float(row['total'])
                for row in qs_base
                .filter(tipo=tipo)
                .annotate(fecha=TruncDate('fecha_registro'))
                .values('fecha')
                .annotate(total=Sum('monto'))
            }

        ing_map = _diarios('INGRESO')
        egr_map = _diarios('EGRESO')

        rango    = [primer_dia + timedelta(days=i)
                    for i in range((hoy - primer_dia).days + 1)]
        labels   = [d.strftime('%d/%m') for d in rango]
        ingresos = [ing_map.get(d, 0) for d in rango]
        egresos  = [egr_map.get(d, 0) for d in rango]

    # ── Mes: todos los meses del año en curso hasta el actual ────
    if granularidad == 'anio':
        labels, ingresos, egresos = [], [], []
        for m in range(1, mes + 1):
            r = ResumenMensual.objects.filter(usuario=user, mes=m, anio=anio).first()
            if r:
                ing = float(r.total_ingresos)
                egr = float(r.total_egresos)
            else:
                _ing, _egr = _totales_movimiento(user, m, anio)
                ing, egr = float(_ing), float(_egr)
            labels.append(MESES_ES[m][:3])
            ingresos.append(ing)
            egresos.append(egr)

    return JsonResponse({
        'ok':           True,
        'granularidad': granularidad,
        'labels':       labels,
        'ingresos':     ingresos,
        'egresos':      egresos,
    })