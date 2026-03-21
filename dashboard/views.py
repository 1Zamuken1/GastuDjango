import json
import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import render

from dashboard.models import ResumenMensual
from movimientos.models import Movimiento
from notificaciones.models import Notificacion
from ahorros.models import AporteAhorro


MESES_ES = {
    1: 'Enero',   2: 'Febrero',  3: 'Marzo',    4: 'Abril',
    5: 'Mayo',    6: 'Junio',    7: 'Julio',     8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}

ZERO = Decimal('0')

PIE_COLORES = [
    '#e11d48', '#f87171', '#fbbf24', '#a3e635',
    '#34d399', '#38bdf8', '#818cf8', '#f472b6',
]


def _ultimo_dia(mes, anio):
    """Devuelve el último día del mes dado."""
    return date(anio, mes, calendar.monthrange(anio, mes)[1])


def _totales_movimiento(user, mes, anio):
    """Calcula ingresos y egresos directamente desde Movimiento (fallback sin ResumenMensual)."""
    qs = Movimiento.objects.filter(
        usuario=user, activo=True,
        fecha_registro__month=mes,
        fecha_registro__year=anio,
    )
    ingresos = qs.filter(tipo='INGRESO').aggregate(t=Sum('monto'))['t'] or ZERO
    egresos  = qs.filter(tipo='EGRESO').aggregate(t=Sum('monto'))['t'] or ZERO
    return ingresos, egresos


def _build_context(user, mes, anio):
    """
    Construye todos los datos del dashboard para un mes/año dado.
    Fuente principal: ResumenMensual (Opcion A — lectura directa, sin recalculo).
    Ahorros se calculan directamente desde AporteAhorro porque ResumenMensual
    no los integra todavia.
    """
    hoy           = date.today()
    es_mes_actual = (mes == hoy.month and anio == hoy.year)
    ultimo_dia    = hoy if es_mes_actual else _ultimo_dia(mes, anio)

    resumen = ResumenMensual.objects.filter(
        usuario=user, mes=mes, anio=anio,
    ).first()

    if resumen:
        total_ingresos = resumen.total_ingresos
        total_egresos  = resumen.total_egresos
        total_ahorros  = resumen.total_ahorros
        utilidad       = resumen.ingreso_neto
        disponible     = resumen.ganancia_acumulada
        hay_deficit    = resumen.deficit
    else:
        total_ingresos, total_egresos = _totales_movimiento(user, mes, anio)
        total_ahorros = ZERO
        utilidad      = total_ingresos - total_egresos
        disponible    = utilidad
        hay_deficit   = total_egresos > total_ingresos

    diferencia = total_ingresos - total_egresos

    # Ahorros del mes (query directa — ResumenMensual.total_ahorros es siempre 0)
    ahorros_mes = (
        AporteAhorro.objects
        .filter(
            ahorro__usuario=user,
            fecha_registro__month=mes,
            fecha_registro__year=anio,
        )
        .aggregate(t=Sum('aporte'))['t'] or ZERO
    )

    # Ahorro total acumulado hasta el ultimo dia del mes visto
    ahorro_total = (
        AporteAhorro.objects
        .filter(
            ahorro__usuario=user,
            fecha_registro__lte=ultimo_dia,
        )
        .aggregate(t=Sum('aporte'))['t'] or ZERO
    )

    # Pie chart — egresos por categoria
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

    pie_labels  = [item['categoria__nombre'] or 'Sin categoria' for item in egresos_cat]
    pie_valores = [float(item['total']) for item in egresos_cat]
    pie_data = {
        'labels':  pie_labels,
        'valores': pie_valores,
        'colores': PIE_COLORES[:len(pie_labels)],
    }

    # Movimientos del mes visto
    ultimos_movimientos = (
        Movimiento.objects
        .filter(
            usuario=user, activo=True,
            fecha_registro__month=mes,
            fecha_registro__year=anio,
        )
        .select_related('categoria')
        .order_by('-fecha_registro')[:10]
    )

    # Notificaciones — siempre las mas recientes, no dependen del mes
    notificaciones_count = Notificacion.objects.filter(
        usuario=user, leida=False,
    ).count()

    ultimas_notificaciones = (
        Notificacion.objects
        .filter(usuario=user)
        .order_by('-fecha_creacion')[:4]
    )

    return {
        'mes':                    mes,
        'anio':                   anio,
        'mes_nombre':             MESES_ES[mes],
        'es_mes_actual':          es_mes_actual,
        'total_ingresos':         total_ingresos,
        'total_egresos':          total_egresos,
        'total_ahorros':          total_ahorros,
        'utilidad':               utilidad,
        'disponible':             disponible,
        'diferencia':             diferencia,
        'ahorro_total':           ahorro_total,
        'ahorros_mes':            ahorros_mes,
        'hay_deficit':            hay_deficit,
        'pie_data':               pie_data,
        'pie_json':               json.dumps(pie_data),
        'ultimos_movimientos':    ultimos_movimientos,
        'notificaciones_count':   notificaciones_count,
        'ultimas_notificaciones': ultimas_notificaciones,
        'hoy':                    hoy,
    }


@login_required
def meses_disponibles(request):
    """
    Devuelve el primer mes/anio con ResumenMensual para el usuario.
    El frontend lo usa para saber hasta donde puede navegar hacia atras.
    Se llama una sola vez al cargar la pagina y se cachea en JS.
    """
    primer = (
        ResumenMensual.objects
        .filter(usuario=request.user)
        .order_by('anio', 'mes')
        .first()
    )
    hoy = date.today()
    return JsonResponse({
        'ok':          True,
        'primer_mes':  primer.mes  if primer else hoy.month,
        'primer_anio': primer.anio if primer else hoy.year,
    })


@login_required
def home_view(request):
    hoy  = date.today()
    user = request.user

    # Parsear y validar mes/anio desde query params
    try:
        mes  = int(request.GET.get('mes',  hoy.month))
        anio = int(request.GET.get('anio', hoy.year))
        if not (1 <= mes <= 12):
            mes = hoy.month
    except (ValueError, TypeError):
        mes, anio = hoy.month, hoy.year

    # No permitir navegar al futuro
    if (anio, mes) > (hoy.year, hoy.month):
        mes, anio = hoy.month, hoy.year

    ctx = _build_context(user, mes, anio)

    # Respuesta JSON para requests AJAX (navegacion sin recarga)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        mov_list = [
            {
                'tipo':        m.tipo,
                'descripcion': m.descripcion or 'Sin descripcion',
                'categoria':   m.categoria.nombre if m.categoria else 'Sin categoria',
                'fecha':       m.fecha_registro.strftime('%d/%m/%Y'),
                'monto':       str(m.monto),
            }
            for m in ctx['ultimos_movimientos']
        ]

        notif_list = [
            {
                'titulo': n.titulo,
                'tipo':   n.tipo,
                'leida':  n.leida,
                'fecha':  n.fecha_creacion.strftime('%d/%m %H:%M'),
            }
            for n in ctx['ultimas_notificaciones']
        ]

        return JsonResponse({
            'ok':                    True,
            'mes':                   mes,
            'anio':                  anio,
            'mes_nombre':            ctx['mes_nombre'],
            'es_mes_actual':         ctx['es_mes_actual'],
            'total_ingresos':        str(ctx['total_ingresos']),
            'total_egresos':         str(ctx['total_egresos']),
            'utilidad':              str(ctx['utilidad']),
            'disponible':            str(ctx['disponible']),
            'diferencia':            str(ctx['diferencia']),
            'ahorro_total':          str(ctx['ahorro_total']),
            'ahorros_mes':           str(ctx['ahorros_mes']),
            'hay_deficit':           ctx['hay_deficit'],
            'pie_data':              ctx['pie_data'],
            'ultimos_movimientos':   mov_list,
            'notificaciones_count':  ctx['notificaciones_count'],
            'ultimas_notificaciones': notif_list,
        })

    return render(request, 'dashboard/home.html', ctx)


@login_required
def tendencia_mes(request):
    """
    Devuelve los totales diarios de ingresos y egresos del mes solicitado.

    Mes actual: rango completo desde dia 1 hasta hoy.
    Meses pasados: solo dias con al menos un movimiento registrado.

    Query params opcionales:
    - mes  (int, 1-12)
    - anio (int)
    """
    hoy  = date.today()
    user = request.user

    try:
        mes  = int(request.GET.get('mes',  hoy.month))
        anio = int(request.GET.get('anio', hoy.year))
    except (ValueError, TypeError):
        mes, anio = hoy.month, hoy.year

    es_mes_actual = (mes == hoy.month and anio == hoy.year)
    primer_dia    = date(anio, mes, 1)

    qs_base = Movimiento.objects.filter(
        usuario=user,
        activo=True,
        fecha_registro__month=mes,
        fecha_registro__year=anio,
    )

    def _diarios(tipo):
        return {
            row['fecha']: float(row['total'])
            for row in (
                qs_base
                .filter(tipo=tipo)
                .annotate(fecha=TruncDate('fecha_registro'))
                .values('fecha')
                .annotate(total=Sum('monto'))
            )
        }

    ing_map = _diarios('INGRESO')
    egr_map = _diarios('EGRESO')

    if es_mes_actual:
        total_dias = (hoy - primer_dia).days + 1
        rango = [primer_dia + timedelta(days=i) for i in range(total_dias)]
    else:
        dias_con_datos = sorted(set(ing_map.keys()) | set(egr_map.keys()))
        rango = dias_con_datos

    if not rango:
        return JsonResponse({
            'ok': True, 'labels': [], 'ingresos': [], 'egresos': [], 'total_dias': 0,
        })

    return JsonResponse({
        'ok':        True,
        'labels':    [str(d.day) for d in rango],
        'ingresos':  [ing_map.get(d, 0) for d in rango],
        'egresos':   [egr_map.get(d, 0) for d in rango],
        'total_dias': len(rango),
    })