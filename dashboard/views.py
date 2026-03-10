import json
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from dashboard.models import ResumenMensual
from movimientos.models import Movimiento
from notificaciones.models import Notificacion


MESES_ES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}


@login_required
def home_view(request):
    """
    Vista principal del dashboard.
    Carga el resumen del mes actual, últimos movimientos,
    egresos por categoría para el gráfico y notificaciones.
    """
    from django.db.models import Sum

    hoy = datetime.now()
    mes = hoy.month
    anio = hoy.year

    resumen = ResumenMensual.objects.filter(
        usuario=request.user, mes=mes, anio=anio
    ).first()

    total_ingresos = resumen.total_ingresos if resumen else Decimal('0')
    total_egresos  = resumen.total_egresos  if resumen else Decimal('0')
    disponible     = resumen.disponible     if resumen else Decimal('0')
    ingreso_neto   = resumen.ingreso_neto   if resumen else Decimal('0')
    hay_deficit    = resumen.deficit        if resumen else False

    ultimos_movimientos = (
        Movimiento.objects
        .filter(usuario=request.user, activo=True)
        .select_related('categoria')
        .order_by('-fecha_registro')[:6]
    )

    egresos_qs = (
        Movimiento.objects
        .filter(
            usuario=request.user,
            tipo='EGRESO',
            activo=True,
            fecha_registro__month=mes,
            fecha_registro__year=anio,
        )
        .values('categoria__nombre')
        .annotate(total=Sum('monto'))
        .order_by('-total')[:5]
    )

    colores_chart = ['#f87171', '#fb923c', '#fbbf24', '#a78bfa', '#94a3b8']
    chart_data = [
        {
            'label': item['categoria__nombre'],
            'value': float(item['total']),
            'color': colores_chart[i % len(colores_chart)],
        }
        for i, item in enumerate(egresos_qs)
    ]

    notificaciones_count = Notificacion.objects.filter(
        usuario=request.user, leida=False
    ).count()

    ultimas_notificaciones = Notificacion.objects.filter(
        usuario=request.user
    ).order_by('-fecha_creacion')[:4]

    context = {
        'resumen':                resumen,
        'total_ingresos':         total_ingresos,
        'total_egresos':          total_egresos,
        'disponible':             disponible,
        'ingreso_neto':           ingreso_neto,
        'hay_deficit':            hay_deficit,
        'ultimos_movimientos':    ultimos_movimientos,
        'chart_data_json':        json.dumps(chart_data),
        'notificaciones_count':   notificaciones_count,
        'ultimas_notificaciones': ultimas_notificaciones,
        'mes_nombre':             MESES_ES[mes],
        'anio':                   anio,
        'hoy':                    hoy,
    }

    return render(request, 'dashboard/home.html', context)