"""
API REST interna para el agente_financiero de GastuApp.
Endpoints bajo /movimientos/api/ — requieren sesión Django autenticada.

Todos los endpoints de lectura usan GET con query params.
Todos los endpoints de escritura usan POST con body JSON.

El CSRF token debe enviarse en el header X-CSRFToken (disponible
en la cookie csrftoken que Django establece en cada respuesta HTML).

Endpoints disponibles:
    GET  /movimientos/api/listar/         — lista con filtros
    GET  /movimientos/api/categorias/     — categorías disponibles
    POST /movimientos/api/crear/          — crear movimiento
    POST /movimientos/api/editar/<pk>/    — editar movimiento
    POST /movimientos/api/eliminar/<pk>/  — eliminar movimiento
"""
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from categorias.models import Categoria
from .models import Movimiento

MESES_ES = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
]


# ── Helpers internos ──────────────────────────────────────────────────────────

def _parse_json_body(request):
    """
    Parsea el body JSON de la request.
    Devuelve dict vacío si el body está vacío o no es JSON válido.
    """
    try:
        return json.loads(request.body) if request.body else {}
    except (json.JSONDecodeError, ValueError):
        return {}


def _serializar_movimiento(mov):
    """
    Serializa una instancia de Movimiento a dict para respuesta JSON.
    Espera que categoria esté en select_related o ya cargada.
    """
    return {
        'id': mov.id,
        'tipo': mov.tipo,
        'monto': str(mov.monto),
        'monto_fmt': f'${mov.monto:,.0f}',
        'descripcion': mov.descripcion or '',
        'categoria_id': mov.categoria_id,
        'categoria_nombre': mov.categoria.nombre,
        'fecha_registro': mov.fecha_registro.strftime('%d/%m/%Y'),
        'fecha_iso': mov.fecha_registro.date().isoformat(),
    }


def _calcular_disponible(usuario, mes, anio, monto_original=Decimal('0')):
    """
    Calcula el saldo disponible del usuario para un mes dado.
    Descuenta monto_original del total de egresos (útil al editar para no
    contar el egreso actual dos veces).
    Devuelve Decimal.
    """
    total_ingresos = (
        Movimiento.objects
        .filter(usuario=usuario, tipo='INGRESO',
                fecha_registro__month=mes, fecha_registro__year=anio)
        .aggregate(t=Sum('monto'))['t'] or Decimal('0')
    )
    total_egresos = (
        Movimiento.objects
        .filter(usuario=usuario, tipo='EGRESO',
                fecha_registro__month=mes, fecha_registro__year=anio)
        .aggregate(t=Sum('monto'))['t'] or Decimal('0')
    )
    return total_ingresos - (total_egresos - monto_original)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@login_required
@require_http_methods(['GET'])
def api_listar_movimientos(request):
    """
    Lista movimientos del usuario autenticado con filtros opcionales.

    GET params:
      tipo        — INGRESO | EGRESO | AMBOS  (default: AMBOS)
      mes         — 1-12                       (default: mes actual)
      anio        — YYYY                       (default: año actual)
      categoria   — id de categoría            (opcional)
      fecha_desde — YYYY-MM-DD                 (opcional, tiene prioridad sobre mes/anio)
      fecha_hasta — YYYY-MM-DD                 (opcional, tiene prioridad sobre mes/anio)
      page        — número de página           (default: 1)
      page_size   — registros por página       (default: 50, máx: 200)

    Si se envían fecha_desde o fecha_hasta, se ignoran mes y anio.

    Respuesta:
      ok          — bool
      movimientos — lista serializada
      paginacion  — total, pagina_actual, total_paginas, desde, hasta
      resumen     — total_ingresos, total_egresos, balance (solo del resultado paginado)
      filtros_aplicados — refleja los parámetros usados
    """
    hoy = timezone.now().date()

    tipo        = request.GET.get('tipo', 'AMBOS').upper()
    mes         = int(request.GET.get('mes',  hoy.month))
    anio        = int(request.GET.get('anio', hoy.year))
    categoria   = request.GET.get('categoria')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    pagina      = int(request.GET.get('page', 1))
    page_size   = min(int(request.GET.get('page_size', 50)), 200)

    qs = (
        Movimiento.objects
        .filter(usuario=request.user)
        .select_related('categoria')
        .order_by('-fecha_registro')
    )

    if tipo in ('INGRESO', 'EGRESO'):
        qs = qs.filter(tipo=tipo)

    # Filtro temporal: rango explícito tiene prioridad sobre mes/anio
    usa_rango = bool(fecha_desde or fecha_hasta)
    if usa_rango:
        if fecha_desde:
            try:
                qs = qs.filter(
                    fecha_registro__date__gte=datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                )
            except ValueError:
                pass
        if fecha_hasta:
            try:
                qs = qs.filter(
                    fecha_registro__date__lte=datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
                )
            except ValueError:
                pass
    else:
        qs = qs.filter(fecha_registro__month=mes, fecha_registro__year=anio)

    if categoria:
        qs = qs.filter(categoria_id=categoria)

    paginator = Paginator(qs, page_size)
    page_obj  = paginator.get_page(pagina)

    movimientos_page = list(page_obj)
    total_ingresos = sum(m.monto for m in movimientos_page if m.tipo == 'INGRESO')
    total_egresos  = sum(m.monto for m in movimientos_page if m.tipo == 'EGRESO')

    return JsonResponse({
        'ok': True,
        'movimientos': [_serializar_movimiento(m) for m in movimientos_page],
        'paginacion': {
            'total': paginator.count,
            'pagina_actual': pagina,
            'total_paginas': paginator.num_pages,
            'desde': page_obj.start_index(),
            'hasta': page_obj.end_index(),
        },
        'resumen': {
            'total_ingresos': str(total_ingresos),
            'total_egresos':  str(total_egresos),
            'balance':        str(total_ingresos - total_egresos),
        },
        'filtros_aplicados': {
            'tipo':       tipo,
            'mes':        mes,
            'anio':       anio,
            'mes_nombre': MESES_ES[mes] if 1 <= mes <= 12 else '',
            'usa_rango':  usa_rango,
        },
    })


@login_required
@require_http_methods(['GET'])
def api_listar_categorias(request):
    """
    Lista las categorías activas disponibles.

    GET params:
      tipo — INGRESO | EGRESO | AMBOS (default: AMBOS)

    Respuesta:
      ok         — bool
      categorias — lista con id, nombre, tipo
    """
    tipo = request.GET.get('tipo', 'AMBOS').upper()

    qs = Categoria.objects.filter(activo=True).order_by('tipo', 'nombre')
    if tipo in ('INGRESO', 'EGRESO'):
        qs = qs.filter(tipo=tipo)

    return JsonResponse({
        'ok': True,
        'categorias': [
            {
                'id':     c.id,
                'nombre': c.nombre,
                'tipo':   c.tipo,
            }
            for c in qs
        ],
    })


@login_required
@require_http_methods(['POST'])
def api_crear_movimiento(request):
    """
    Crea un nuevo movimiento para el usuario autenticado.

    Body JSON:
      tipo        — INGRESO | EGRESO     (requerido)
      categoria   — id de la categoría   (requerido)
      monto       — número positivo      (requerido)
      descripcion — texto libre          (opcional)

    Validaciones de negocio:
      - La categoría debe existir, estar activa y coincidir con el tipo.
      - Para EGRESO: el monto no puede superar el saldo disponible del mes
        actual (ingresos_mes - egresos_mes).

    Respuesta exitosa (HTTP 201):
      ok         — True
      movimiento — objeto serializado

    Respuesta de error (HTTP 400):
      ok     — False
      errors — dict campo → mensaje
    """
    data    = _parse_json_body(request)
    errores = {}

    # Validar tipo
    tipo = (data.get('tipo') or '').upper()
    if tipo not in ('INGRESO', 'EGRESO'):
        errores['tipo'] = 'Debe ser INGRESO o EGRESO.'

    # Validar categoría
    categoria = None
    categoria_id = data.get('categoria')
    if not categoria_id:
        errores['categoria'] = 'La categoría es obligatoria.'
    elif not errores.get('tipo'):
        try:
            categoria = Categoria.objects.get(pk=categoria_id, activo=True, tipo=tipo)
        except Categoria.DoesNotExist:
            errores['categoria'] = f'Categoría no válida o no corresponde al tipo {tipo}.'

    # Validar monto
    monto = None
    raw_monto = data.get('monto')
    if raw_monto is None or str(raw_monto).strip() == '':
        errores['monto'] = 'El monto es obligatorio.'
    else:
        try:
            monto = Decimal(str(raw_monto))
            if monto <= 0:
                errores['monto'] = 'El monto debe ser mayor a cero.'
        except (InvalidOperation, TypeError):
            errores['monto'] = 'Monto inválido. Usa un número como 15000 o 15000.50'

    # Validar disponible para egresos
    if not errores and tipo == 'EGRESO':
        hoy = timezone.now().date()
        disponible = _calcular_disponible(request.user, hoy.month, hoy.year)
        if monto > disponible:
            errores['monto'] = (
                f'El monto (${monto:,.0f}) supera el saldo disponible del mes '
                f'(${disponible:,.0f}). Registra un ingreso primero o reduce el monto.'
            )

    if errores:
        return JsonResponse({'ok': False, 'errors': errores}, status=400)

    mov = Movimiento.objects.create(
        usuario=request.user,
        tipo=tipo,
        categoria=categoria,
        monto=monto,
        descripcion=(data.get('descripcion') or '').strip() or None,
    )

    return JsonResponse({'ok': True, 'movimiento': _serializar_movimiento(mov)}, status=201)


@login_required
@require_http_methods(['POST'])
def api_editar_movimiento(request, pk):
    """
    Edita un movimiento existente. Solo el dueño puede editarlo.

    Body JSON (todos los campos son opcionales — solo se actualizan los enviados):
      categoria   — id de la categoría (debe coincidir con el tipo del movimiento)
      monto       — número positivo
      descripcion — texto libre

    Nota: el tipo no se puede cambiar una vez registrado el movimiento.

    Validaciones de negocio:
      - Para EGRESO: si cambia el monto, no puede superar el disponible
        del mes (descontando el monto original para no bloquear la edición).

    Respuesta exitosa (HTTP 200):
      ok         — True
      movimiento — objeto serializado actualizado

    Respuesta de error (HTTP 400):
      ok     — False
      errors — dict campo → mensaje
    """
    mov     = get_object_or_404(Movimiento, pk=pk, usuario=request.user)
    data    = _parse_json_body(request)
    errores = {}

    # Categoría — opcional, pero si se envía debe ser válida y del mismo tipo
    categoria = mov.categoria
    if 'categoria' in data:
        try:
            categoria = Categoria.objects.get(
                pk=data['categoria'], activo=True, tipo=mov.tipo
            )
        except Categoria.DoesNotExist:
            errores['categoria'] = (
                f'Categoría no válida o no corresponde al tipo {mov.tipo}.'
            )

    # Monto — opcional, pero si se envía debe ser positivo
    monto = mov.monto
    if 'monto' in data:
        try:
            monto = Decimal(str(data['monto']))
            if monto <= 0:
                errores['monto'] = 'El monto debe ser mayor a cero.'
        except (InvalidOperation, TypeError):
            errores['monto'] = 'Monto inválido. Usa un número como 15000 o 15000.50'

    # Validar disponible para egresos solo si el monto cambia
    if not errores and mov.tipo == 'EGRESO' and 'monto' in data:
        hoy = timezone.now().date()
        disponible = _calcular_disponible(
            request.user, hoy.month, hoy.year,
            monto_original=mov.monto,
        )
        if monto > disponible:
            errores['monto'] = (
                f'El monto (${monto:,.0f}) supera el saldo disponible del mes '
                f'(${disponible:,.0f}).'
            )

    if errores:
        return JsonResponse({'ok': False, 'errors': errores}, status=400)

    mov.categoria = categoria
    mov.monto     = monto
    if 'descripcion' in data:
        mov.descripcion = (data['descripcion'] or '').strip() or None
    mov.save()

    # Recargar con select_related para tener categoria.nombre actualizado
    mov.refresh_from_db()
    mov.categoria  # ya cargado por refresh; acceder para evitar query extra en serializar
    # Forzar carga de categoria tras refresh
    mov = Movimiento.objects.select_related('categoria').get(pk=mov.pk)

    return JsonResponse({'ok': True, 'movimiento': _serializar_movimiento(mov)})


@login_required
@require_http_methods(['POST'])
def api_eliminar_movimiento(request, pk):
    """
    Elimina un movimiento. Solo el dueño puede eliminarlo.

    No requiere body — el pk en la URL es suficiente.

    Respuesta exitosa (HTTP 200):
      ok — True
      id — pk del movimiento eliminado
    """
    mov = get_object_or_404(Movimiento, pk=pk, usuario=request.user)
    mov.delete()
    return JsonResponse({'ok': True, 'id': pk})