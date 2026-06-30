"""
Vistas del dashboard.

Orquestan requests HTTP y delegan toda la logica de negocio
a dashboard.services. No contienen queries directas a modelos.
"""
from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from gastu_django.constants import MESES_ES
from .services import (
    build_dashboard_context,
    build_tendencia_data,
    obtener_items_completos_mes,
)
from .models import ResumenMensual


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

def extract_filters(request):
    """Extrae los filtros avanzados de la query string o del body POST."""
    filtros = {}
    req = request.POST if request.method == 'POST' else request.GET
    if req.get('min_monto'): filtros['min_monto'] = req.get('min_monto')
    if req.get('max_monto'): filtros['max_monto'] = req.get('max_monto')
    if req.get('categoria_id'): filtros['categoria_id'] = req.get('categoria_id')
    if req.get('tipo'): filtros['tipo'] = req.get('tipo')
    if req.get('fecha_inicio'): filtros['fecha_inicio'] = req.get('fecha_inicio')
    if req.get('fecha_fin'): filtros['fecha_fin'] = req.get('fecha_fin')
    return filtros



@login_required
def home_view(request):
    """Vista principal del dashboard. Soporta carga HTML y navegacion AJAX."""
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

    # Permitir navegar a cualquier mes (los meses futuros o pasados sin datos se mostrarán vacíos)
    filtros = extract_filters(request)
    ctx = build_dashboard_context(user, mes, anio, filtros=filtros)

    # Verificar Onboarding: Si el usuario no tiene movimientos, mostrar modal de saldo inicial
    from movimientos.models import Movimiento
    from categorias.models import Categoria
    requiere_onboarding = not Movimiento.objects.filter(usuario=user).exists()
    ctx['requiere_onboarding'] = requiere_onboarding
    if requiere_onboarding:
        cat_ajuste, _ = Categoria.objects.get_or_create(
            nombre='Saldo Inicial',
            tipo='INGRESO',
            defaults={'descripcion': 'Ajuste de saldo inicial', 'activo': True, 'es_sistema': True}
        )
        ctx['onboarding_categoria_id'] = cat_ajuste.id

    # Categorías ahora se cargan dinámicamente via /api/categorias/enriched/
    ctx['filtros_activos'] = filtros

    # Respuesta JSON para requests AJAX (navegacion sin recarga)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        mov_list = [
            {
                'tipo':        m['tipo'],
                'descripcion': m['descripcion'],
                'categoria':   m['categoria'],
                'fecha':       m['fecha_fmt'],
                'monto':       str(m['monto']),
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
            'ok':                       True,
            'mes':                      mes,
            'anio':                     anio,
            'mes_nombre':               ctx['mes_nombre'],
            'es_mes_actual':            ctx['es_mes_actual'],
            'total_ingresos':           str(ctx['total_ingresos']),
            'total_egresos':            str(ctx['total_egresos']),
            'utilidad':                 str(ctx['utilidad']),
            'disponible_global':        str(ctx['disponible_global']),
            'total_dinero':             str(ctx['total_dinero']),
            'diferencia':               str(ctx['diferencia']),
            'ahorro_total':             str(ctx['ahorro_total']),
            'ahorros_mes':              str(ctx['ahorros_mes']),
            'hay_deficit':              ctx['hay_deficit'],
            'pie_data':                 ctx['pie_data'],
            'metas_ahorro_activas':     ctx['metas_ahorro_activas'],
            'ultimos_movimientos':      mov_list,
            'notificaciones_count':     ctx['notificaciones_count'],
            'ultimas_notificaciones':   notif_list,
            'tiene_filtros':            ctx['tiene_filtros'],
        })

    return render(request, 'dashboard/home.html', ctx)


@login_required
def tendencia_mes(request):
    """
    Devuelve los totales diarios de ingresos y egresos del mes solicitado.

    Query params opcionales:
    - mes  (int, 1-12)
    - anio (int)
    """
    hoy = date.today()

    try:
        mes  = int(request.GET.get('mes',  hoy.month))
        anio = int(request.GET.get('anio', hoy.year))
    except (ValueError, TypeError):
        mes, anio = hoy.month, hoy.year

    filtros = extract_filters(request)
    data = build_tendencia_data(request.user, mes, anio, filtros=filtros)
    return JsonResponse(data)


# ── Exportaciones del dashboard ──────────────────────────────────────────────

@login_required
def exportar_excel(request):
    """Exporta el reporte mensual del dashboard a Excel."""
    from dashboard.export_services import generar_excel_dashboard

    hoy  = date.today()
    user = request.user
    req  = request.POST if request.method == 'POST' else request.GET
    mes  = int(req.get('mes', hoy.month))
    anio = int(req.get('anio', hoy.year))
    
    filtros = extract_filters(request)
    ctx       = build_dashboard_context(user, mes, anio, filtros=filtros)
    all_items = obtener_items_completos_mes(user, mes, anio, filtros=filtros)

    return generar_excel_dashboard(ctx, all_items, mes, anio)


@login_required
def exportar_pdf(request):
    """Exporta el reporte mensual del dashboard a PDF."""
    from dashboard.export_services import generar_pdf_dashboard

    hoy  = date.today()
    user = request.user
    req  = request.POST if request.method == 'POST' else request.GET
    mes  = int(req.get('mes', hoy.month))
    anio = int(req.get('anio', hoy.year))
    
    filtros = extract_filters(request)
    ctx       = build_dashboard_context(user, mes, anio, filtros=filtros)
    
    # Agregar gráficos si vienen en el POST
    if request.method == 'POST':
        ctx['img_tendencia'] = request.POST.get('img_tendencia', '')
        ctx['img_pie'] = request.POST.get('img_pie', '')

    ctx['filtro_tipo'] = filtros.get('tipo', '')

    all_items = obtener_items_completos_mes(user, mes, anio, filtros=filtros)

    return generar_pdf_dashboard(ctx, all_items, mes, anio, user)


# ── Onboarding ────────────────────────────────────────────────────────────────

@login_required
def guardar_saldo_inicial(request):
    """
    Vista exclusiva del onboarding: crea el movimiento de Saldo Inicial
    sin pasar por MovimientoForm (que excluye categorías de sistema).
    Solo acepta POST con CSRF y AJAX.
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Método no permitido.'}, status=405)

    from decimal import Decimal, InvalidOperation
    from django.utils import timezone
    from movimientos.models import Movimiento
    from categorias.models import Categoria

    # Validar que el usuario realmente no tenga movimientos (evita llamadas duplicadas)
    if Movimiento.objects.filter(usuario=request.user).exists():
        return JsonResponse({'ok': False, 'error': 'El saldo inicial ya fue registrado.'}, status=400)

    # Validar monto
    try:
        monto = Decimal(request.POST.get('monto', '0'))
        if monto <= 0:
            return JsonResponse({'ok': False, 'error': 'El monto debe ser mayor que cero.'}, status=400)
    except InvalidOperation:
        return JsonResponse({'ok': False, 'error': 'Monto inválido.'}, status=400)

    # Obtener o crear la categoría de sistema
    cat, _ = Categoria.objects.get_or_create(
        nombre='Saldo Inicial',
        tipo='INGRESO',
        defaults={'descripcion': 'Ajuste de saldo inicial', 'activo': True, 'es_sistema': True},
    )

    mov = Movimiento.objects.create(
        usuario=request.user,
        tipo='INGRESO',
        descripcion='Saldo Inicial',
        categoria=cat,
        monto=monto,
        fecha_registro=timezone.localdate(),
    )

    return JsonResponse({'ok': True, 'id': mov.id})