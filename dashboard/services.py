"""
Servicios de negocio del dashboard.

Contiene la logica de calculo de resumenes mensuales, saldo disponible
y construccion de contexto para las vistas. Las vistas solo orquestan
y delegan a estas funciones.
"""
import json
import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncDate

from gastu_django.constants import ZERO, MESES_ES, PIE_COLORES
from movimientos.models import Movimiento


# ── Actualizar ResumenMensual (llamado por signals) ──────────────────────────

def actualizar_resumen(usuario, mes, anio):
    """
    Calcula y actualiza el ResumenMensual de un usuario para un mes dado.
    Se llama automaticamente desde los signals de Movimiento.

    Campos almacenados:
    - total_ingresos, total_egresos, total_ahorros : totales del mes
    - ingreso_neto   : ingresos - egresos - ahorros (utilidad mensual)
    - disponible     : igual a ingreso_neto por mes
    - ganancia_acumulada : suma historica de todos los ingreso_neto hasta este mes
    - ahorro_total   : suma historica de todos los total_ahorros hasta este mes

    Args:
        usuario: instancia del usuario autenticado.
        mes (int): mes a recalcular (1-12).
        anio (int): ano a recalcular.
    """
    from .models import ResumenMensual

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

    from ahorros.models import AporteAhorro

    total_ahorros = AporteAhorro.objects.filter(
        ahorro__usuario=usuario,
        estado_ap='APORTADO',
        fecha_registro__month=mes,
        fecha_registro__year=anio,
    ).aggregate(total=Sum('aporte'))['total'] or ZERO

    ingreso_neto = total_ingresos - total_egresos - total_ahorros

    # Acumulados historicos
    anteriores = ResumenMensual.objects.filter(
        usuario=usuario,
    ).exclude(mes=mes, anio=anio)

    ahorro_total = (
        anteriores.aggregate(total=Sum('total_ahorros'))['total'] or ZERO
    ) + total_ahorros

    # Total dinero usuario: Todos los ingresos - Todos los egresos (sin restar ahorros)
    ingresos_historicos = Movimiento.objects.filter(usuario=usuario, tipo='INGRESO', activo=True).aggregate(t=Sum('monto'))['t'] or ZERO
    egresos_historicos = Movimiento.objects.filter(usuario=usuario, tipo='EGRESO', activo=True).aggregate(t=Sum('monto'))['t'] or ZERO
    ganancia_acumulada = ingresos_historicos - egresos_historicos

    # Disponible: Ganancia acumulada real - Ahorros totales
    disponible = ganancia_acumulada - ahorro_total

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

    # Invalidar caché del dashboard
    from django.core.cache import cache
    cache.delete(f'dashboard_ctx_{usuario.id}_{mes}_{anio}')
    cache.delete(f'tendencia_data_{usuario.id}_{mes}_{anio}')


# ── Saldo disponible (fuente unica de verdad) ───────────────────────────────

def obtener_disponible(usuario, mes, anio, monto_original=None):
    """
    Devuelve el saldo disponible global del usuario.
    """
    from .models import ResumenMensual
    from ahorros.models import AporteAhorro

    ingresos_historicos = Movimiento.objects.filter(usuario=usuario, tipo='INGRESO', activo=True).aggregate(t=Sum('monto'))['t'] or ZERO
    egresos_historicos = Movimiento.objects.filter(usuario=usuario, tipo='EGRESO', activo=True).aggregate(t=Sum('monto'))['t'] or ZERO
    ahorros_historicos = AporteAhorro.objects.filter(ahorro__usuario=usuario, estado_ap='APORTADO').aggregate(t=Sum('aporte'))['t'] or ZERO
    
    disponible_base = ingresos_historicos - egresos_historicos - ahorros_historicos

    if monto_original is not None:
        return disponible_base + monto_original
    return disponible_base


# ── Helpers internos ─────────────────────────────────────────────────────────

def _ultimo_dia(mes, anio):
    """Devuelve el ultimo dia del mes dado."""
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


# ── Construccion del contexto del dashboard ──────────────────────────────────

def build_dashboard_context(user, mes, anio, filtros=None):
    """
    Construye todos los datos del dashboard para un mes/anio dado.
    Fuente principal: ResumenMensual (lectura directa, sin recalculo).
    Ahorros se calculan directamente desde AporteAhorro porque ResumenMensual
    no los integra todavia.

    Args:
        user: instancia del usuario.
        mes (int): mes a consultar.
        anio (int): ano a consultar.

    Returns:
        dict: contexto completo para la vista del dashboard.
    """
    from .models import ResumenMensual
    from ahorros.models import AporteAhorro, AhorroMeta
    from notificaciones.models import Notificacion
    from django.core.cache import cache

    filtros = filtros or {}
    tiene_filtros = bool(filtros)

    cache_key = f'dashboard_ctx_{user.id}_{mes}_{anio}'
    if not tiene_filtros:
        ctx = cache.get(cache_key)
        if ctx:
            return ctx

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
        disponible_global = resumen.disponible
        total_dinero   = resumen.ganancia_acumulada
        hay_deficit    = resumen.deficit
    else:
        total_ingresos, total_egresos = _totales_movimiento(user, mes, anio)
        total_ahorros = (
            AporteAhorro.objects.filter(
                ahorro__usuario=user, estado_ap='APORTADO',
                fecha_registro__month=mes, fecha_registro__year=anio
            ).aggregate(t=Sum('aporte'))['t'] or ZERO
        )
        utilidad = total_ingresos - total_egresos - total_ahorros
        hay_deficit = total_egresos > total_ingresos
        
        ingresos_historicos = Movimiento.objects.filter(usuario=user, tipo='INGRESO', activo=True).aggregate(t=Sum('monto'))['t'] or ZERO
        egresos_historicos = Movimiento.objects.filter(usuario=user, tipo='EGRESO', activo=True).aggregate(t=Sum('monto'))['t'] or ZERO
        ahorros_historicos = AporteAhorro.objects.filter(ahorro__usuario=user, estado_ap='APORTADO').aggregate(t=Sum('aporte'))['t'] or ZERO
        
        total_dinero = ingresos_historicos - egresos_historicos
        disponible_global = total_dinero - ahorros_historicos

    diferencia = total_ingresos - total_egresos

    # Usamos el total_ahorros ya calculado (que respeta estado_ap='APORTADO')
    ahorros_mes = total_ahorros

    # Ahorro total acumulado hasta el ultimo dia del mes visto
    ahorro_total = (
        AporteAhorro.objects
        .filter(
            ahorro__usuario=user,
            fecha_registro__lte=ultimo_dia,
        )
        .aggregate(t=Sum('aporte'))['t'] or ZERO
    )

    pie_data   = _build_pie_data(user, mes, anio, filtros)
    metas      = _build_metas_ahorro(user)
    ultimos    = _build_ultimos_movimientos(user, mes, anio, filtros)
    notif_data = _build_notificaciones(user)

    ctx = {
        'mes':                       mes,
        'anio':                      anio,
        'mes_nombre':                MESES_ES[mes],
        'es_mes_actual':             es_mes_actual,
        'total_ingresos':            total_ingresos,
        'total_egresos':             total_egresos,
        'total_ahorros':             total_ahorros,
        'utilidad':                  utilidad,
        'disponible_global':         disponible_global,
        'total_dinero':              total_dinero,
        'diferencia':                diferencia,
        'ahorro_total':              ahorro_total,
        'ahorros_mes':               ahorros_mes,
        'hay_deficit':               hay_deficit,
        'pie_data':                  pie_data,
        'pie_json':                  json.dumps(pie_data),
        'metas_ahorro_activas':      metas,
        'ultimos_movimientos':       ultimos,
        'notificaciones_count':      notif_data['count'],
        'ultimas_notificaciones':    notif_data['ultimas'],
        'hoy':                       date.today(),
    }
    ctx['tiene_filtros'] = tiene_filtros
    
    if not tiene_filtros:
        cache.set(cache_key, ctx, timeout=60*60*24)
    return ctx


def _build_pie_data(user, mes, anio, filtros=None):
    """Construye datos para el grafico de distribucion de egresos."""
    filtros = filtros or {}
    qs = Movimiento.objects.filter(
        usuario=user, tipo='EGRESO', activo=True,
        fecha_registro__month=mes,
        fecha_registro__year=anio,
    )
    if filtros.get('min_monto'): qs = qs.filter(monto__gte=filtros['min_monto'])
    if filtros.get('max_monto'): qs = qs.filter(monto__lte=filtros['max_monto'])
    if filtros.get('categoria_id'): qs = qs.filter(categoria_id=filtros['categoria_id'])

    egresos_cat = (
        qs
        .values('categoria__nombre')
        .annotate(total=Sum('monto'))
        .order_by('-total')[:8]
    )

    pie_labels  = [item['categoria__nombre'] or 'Sin categoria' for item in egresos_cat]
    pie_valores = [float(item['total']) for item in egresos_cat]
    return {
        'labels':  pie_labels,
        'valores': pie_valores,
        'colores': PIE_COLORES[:len(pie_labels)],
    }


def _build_metas_ahorro(user):
    """Obtiene las metas de ahorro activas del usuario."""
    from ahorros.models import AhorroMeta

    metas_raw = (
        AhorroMeta.objects
        .filter(usuario=user, estado='ACTIVO')
        .select_related('categoria')
        .order_by('-fecha_creacion')[:5]
    )
    metas = []
    for m in metas_raw:
        meta_monto = float(m.monto_meta) if m.monto_meta else 1
        acumulado  = float(m.total_acumulado) if m.total_acumulado else 0
        pct = min(round(acumulado / meta_monto * 100, 1), 100) if meta_monto > 0 else 0
        metas.append({
            'descripcion':   m.descripcion or m.categoria.nombre,
            'categoria':     m.categoria.nombre if m.categoria else 'Sin categoria',
            'acumulado':     acumulado,
            'acumulado_fmt': f"${acumulado:,.0f}",
            'meta':          meta_monto,
            'meta_fmt':      f"${meta_monto:,.0f}",
            'pct':           pct,
            'frecuencia':    m.get_frecuencia_display(),
        })
    return metas


def _build_ultimos_movimientos(user, mes, anio, filtros=None):
    """Obtiene los movimientos y aportes de ahorro del mes, unificados y opcionalmente filtrados."""
    from ahorros.models import AporteAhorro
    filtros = filtros or {}
    tiene_filtros = bool(filtros)

    qs_mov = Movimiento.objects.filter(
        usuario=user, activo=True,
        fecha_registro__month=mes, fecha_registro__year=anio,
    )
    qs_ahor = AporteAhorro.objects.filter(
        ahorro__usuario=user, estado_ap='APORTADO',
        fecha_registro__month=mes, fecha_registro__year=anio,
    )

    if filtros.get('min_monto'):
        qs_mov = qs_mov.filter(monto__gte=filtros['min_monto'])
        qs_ahor = qs_ahor.filter(aporte__gte=filtros['min_monto'])
    if filtros.get('max_monto'):
        qs_mov = qs_mov.filter(monto__lte=filtros['max_monto'])
        qs_ahor = qs_ahor.filter(aporte__lte=filtros['max_monto'])
    if filtros.get('categoria_id'):
        qs_mov = qs_mov.filter(categoria_id=filtros['categoria_id'])
        qs_ahor = qs_ahor.filter(ahorro__categoria_id=filtros['categoria_id'])
    
    tipo_filtro = filtros.get('tipo')
    
    # Aplicar filtro de tipo si existe y no es "todos"
    if tipo_filtro and tipo_filtro != 'todos':
        if tipo_filtro in ['INGRESO', 'EGRESO']:
            qs_mov = qs_mov.filter(tipo=tipo_filtro)
            qs_ahor = qs_ahor.none()
        elif tipo_filtro == 'AHORRO':
            qs_mov = qs_mov.none()

    if not tiene_filtros:
        qs_mov = qs_mov.order_by('-fecha_registro')[:15]
        qs_ahor = qs_ahor.order_by('-fecha_registro')[:15]
    else:
        qs_mov = qs_mov.order_by('-fecha_registro')
        qs_ahor = qs_ahor.order_by('-fecha_registro')

    movs_raw = list(qs_mov.select_related('categoria'))
    ahorros_raw = list(qs_ahor.select_related('ahorro', 'ahorro__categoria'))

    movs_norm = [
        {
            'tipo':        m.tipo,
            'descripcion': m.descripcion or 'Sin descripcion',
            'categoria':   m.categoria.nombre if m.categoria else 'Sin categoria',
            'fecha':       m.fecha_registro,
            'fecha_fmt':   m.fecha_registro.strftime('%d/%m/%Y'),
            'monto':       float(m.monto),
        }
        for m in movs_raw
    ]
    ahor_norm = [
        {
            'tipo':        'AHORRO',
            'descripcion': a.ahorro.descripcion or 'Aporte de ahorro',
            'categoria':   a.ahorro.categoria.nombre if a.ahorro.categoria else 'Sin categoria',
            'fecha':       a.fecha_registro,
            'fecha_fmt':   a.fecha_registro.strftime('%d/%m/%Y'),
            'monto':       float(a.aporte),
        }
        for a in ahorros_raw
    ]

    res = sorted(
        movs_norm + ahor_norm,
        key=lambda x: str(x['fecha']),
        reverse=True,
    )
    return res if tiene_filtros else res[:10]


def _build_notificaciones(user):
    """Obtiene el conteo y las ultimas notificaciones del usuario."""
    from notificaciones.models import Notificacion

    count = Notificacion.objects.filter(
        usuario=user, leida=False,
    ).count()

    ultimas = (
        Notificacion.objects
        .filter(usuario=user)
        .order_by('-fecha_creacion')[:4]
    )

    return {'count': count, 'ultimas': ultimas}


# ── Datos de tendencia mensual ───────────────────────────────────────────────

def build_tendencia_data(user, mes, anio, filtros=None):
    """
    Construye los datos de tendencia diaria (ingresos, egresos, ahorros)
    para el grafico del dashboard.

    Mes actual: rango completo desde dia 1 hasta hoy.
    Meses pasados: solo dias con al menos un movimiento registrado.

    Args:
        user: instancia del usuario.
        mes (int): mes a consultar.
        anio (int): ano a consultar.

    Returns:
        dict: datos listos para JsonResponse.
    """
    from collections import defaultdict
    from ahorros.models import AporteAhorro
    from django.core.cache import cache

    filtros = filtros or {}
    tiene_filtros = bool(filtros)

    cache_key = f'tendencia_data_{user.id}_{mes}_{anio}'
    if not tiene_filtros:
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

    hoy           = date.today()
    es_mes_actual = (mes == hoy.month and anio == hoy.year)
    primer_dia    = date(anio, mes, 1)

    qs_base = Movimiento.objects.filter(
        usuario=user,
        activo=True,
        fecha_registro__month=mes,
        fecha_registro__year=anio,
    )
    if filtros.get('min_monto'): qs_base = qs_base.filter(monto__gte=filtros['min_monto'])
    if filtros.get('max_monto'): qs_base = qs_base.filter(monto__lte=filtros['max_monto'])
    if filtros.get('categoria_id'): qs_base = qs_base.filter(categoria_id=filtros['categoria_id'])
    
    tipo_filtro = filtros.get('tipo')
    if tipo_filtro == 'AHORRO': qs_base = qs_base.none()
    elif tipo_filtro in ['INGRESO', 'EGRESO']: qs_base = qs_base.filter(tipo=tipo_filtro)

    def _diarios_totales(tipo):
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

    def _diarios_por_categoria(tipo):
        resultado = defaultdict(list)
        rows = (
            qs_base
            .filter(tipo=tipo)
            .annotate(fecha=TruncDate('fecha_registro'))
            .values('fecha', 'categoria__nombre')
            .annotate(total=Sum('monto'))
            .order_by('fecha', '-total')
        )
        for row in rows:
            resultado[row['fecha']].append({
                'nombre': row['categoria__nombre'] or 'Sin categoria',
                'monto':  float(row['total']),
            })
        return dict(resultado)

    ing_map     = _diarios_totales('INGRESO')
    egr_map     = _diarios_totales('EGRESO')
    ing_cat_map = _diarios_por_categoria('INGRESO')
    egr_cat_map = _diarios_por_categoria('EGRESO')

    qs_ahorros = AporteAhorro.objects.filter(
        ahorro__usuario=user,
        estado_ap='APORTADO',
        fecha_registro__month=mes,
        fecha_registro__year=anio,
    )
    if filtros.get('min_monto'): qs_ahorros = qs_ahorros.filter(aporte__gte=filtros['min_monto'])
    if filtros.get('max_monto'): qs_ahorros = qs_ahorros.filter(aporte__lte=filtros['max_monto'])
    if filtros.get('categoria_id'): qs_ahorros = qs_ahorros.filter(ahorro__categoria_id=filtros['categoria_id'])
    
    if tipo_filtro in ['INGRESO', 'EGRESO']: qs_ahorros = qs_ahorros.none()

    ahor_map = {
        row['fecha_registro']: float(row['total'])
        for row in (
            qs_ahorros
            .values('fecha_registro')
            .annotate(total=Sum('aporte'))
        )
    }

    ahor_cat_map = defaultdict(list)
    for row in (
        qs_ahorros
        .values('fecha_registro', 'ahorro__categoria__nombre')
        .annotate(total=Sum('aporte'))
        .order_by('fecha_registro', '-total')
    ):
        ahor_cat_map[row['fecha_registro']].append({
            'nombre': row['ahorro__categoria__nombre'] or 'Sin categoria',
            'monto':  float(row['total']),
        })
    ahor_cat_map = dict(ahor_cat_map)

    if es_mes_actual:
        total_dias = (hoy - primer_dia).days + 1
        rango = [primer_dia + timedelta(days=i) for i in range(total_dias)]
    else:
        dias_con_datos = sorted(
            set(ing_map.keys()) | set(egr_map.keys()) | set(ahor_map.keys())
        )
        rango = dias_con_datos

    if not rango:
        return {
            'ok': True, 'labels': [], 'ingresos': [], 'egresos': [],
            'ahorros': [], 'detalle_ing': {}, 'detalle_egr': {},
            'detalle_ahor': {}, 'total_dias': 0,
        }

    detalle_ing = {
        str(d.day): ing_cat_map.get(d, [])
        for d in rango if d in ing_cat_map
    }
    detalle_egr = {
        str(d.day): egr_cat_map.get(d, [])
        for d in rango if d in egr_cat_map
    }
    detalle_ahor = {
        str(d.day): ahor_cat_map.get(d, [])
        for d in rango if d in ahor_cat_map
    }

    res = {
        'ok':           True,
        'labels':       [str(d.day) for d in rango],
        'ingresos':     [ing_map.get(d, 0) for d in rango],
        'egresos':      [egr_map.get(d, 0) for d in rango],
        'ahorros':      [ahor_map.get(d, 0) for d in rango],
        'detalle_ing':  detalle_ing,
        'detalle_egr':  detalle_egr,
        'detalle_ahor': detalle_ahor,
        'total_dias':   len(rango),
    }
    
    if not tiene_filtros:
        cache.set(cache_key, res, timeout=60*60*24)
        
    return res


# ── Datos completos del mes para exportaciones ───────────────────────────────

def obtener_items_completos_mes(user, mes, anio, filtros=None):
    """
    Obtiene TODOS los movimientos y aportes de ahorro del mes,
    normalizados en una lista de dicts ordenada por fecha descendente.

    Usado por las vistas de exportacion del dashboard (Excel y PDF).

    Args:
        user: instancia del usuario.
        mes (int): mes a consultar.
        anio (int): ano a consultar.

    Returns:
        list[dict]: items con claves tipo, descripcion, categoria, fecha, sort_key, monto.
    """
    from ahorros.models import AporteAhorro

    filtros = filtros or {}

    qs_mov = Movimiento.objects.filter(
        usuario=user, activo=True,
        fecha_registro__month=mes, fecha_registro__year=anio,
    )
    qs_ahor = AporteAhorro.objects.filter(
        ahorro__usuario=user, estado_ap='APORTADO',
        fecha_registro__month=mes, fecha_registro__year=anio,
    )

    if filtros.get('min_monto'):
        qs_mov = qs_mov.filter(monto__gte=filtros['min_monto'])
        qs_ahor = qs_ahor.filter(aporte__gte=filtros['min_monto'])
    if filtros.get('max_monto'):
        qs_mov = qs_mov.filter(monto__lte=filtros['max_monto'])
        qs_ahor = qs_ahor.filter(aporte__lte=filtros['max_monto'])
    if filtros.get('categoria_id'):
        qs_mov = qs_mov.filter(categoria_id=filtros['categoria_id'])
        qs_ahor = qs_ahor.filter(ahorro__categoria_id=filtros['categoria_id'])
    
    tipo_filtro = filtros.get('tipo')
    if tipo_filtro and tipo_filtro != 'todos':
        if tipo_filtro in ['INGRESO', 'EGRESO']:
            qs_mov = qs_mov.filter(tipo=tipo_filtro)
            qs_ahor = qs_ahor.none()
        elif tipo_filtro == 'AHORRO':
            qs_mov = qs_mov.none()

    movs_all = list(qs_mov.select_related('categoria').order_by('-fecha_registro'))
    ahor_all = list(qs_ahor.select_related('ahorro', 'ahorro__categoria').order_by('-fecha_registro'))

    return sorted(
        [
            {
                'tipo': m.tipo, 'descripcion': m.descripcion or 'Sin descripcion',
                'categoria': m.categoria.nombre if m.categoria else '\u2014',
                'fecha': m.fecha_registro.strftime('%d/%m/%Y'),
                'sort_key': str(m.fecha_registro),
                'monto': float(m.monto),
            } for m in movs_all
        ] + [
            {
                'tipo': 'AHORRO', 'descripcion': a.ahorro.descripcion or 'Aporte',
                'categoria': a.ahorro.categoria.nombre if a.ahorro.categoria else '\u2014',
                'fecha': a.fecha_registro.strftime('%d/%m/%Y'),
                'sort_key': str(a.fecha_registro),
                'monto': float(a.aporte),
            } for a in ahor_all
        ],
        key=lambda x: x['sort_key'],
        reverse=True,
    )