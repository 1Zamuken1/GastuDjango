"""
Vistas de la captura bancaria.

- ingesta: punto de entrada interno del servidor SMTP (protegido por token).
- api_*: endpoints JSON para la interfaz del usuario (sesion Django + CSRF).
"""
import hmac
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from categorias.models import Categoria

from . import services
from .models import BuzonCaptura, MovimientoDetectado, ReglaComercio
from .parsers import PARSERS, remitente_es_del_banco
from .parsers.base import normalizar_comercio

MAX_CORREO_BYTES = 5 * 1024 * 1024
MAX_LOTE = 100


# ── Ingesta interna ─────────────────────────────────────────────

@csrf_exempt
@require_POST
def ingesta(request):
    """
    Recibe un correo crudo desde el servidor SMTP.

    Cabeceras: X-Captura-Token (secreto compartido) y X-Captura-Destinatario
    (direccion del sobre SMTP). El cuerpo es el correo completo en bytes.
    Responde 404 si el alias no existe, para que el SMTP rechace con 550.
    """
    esperado = settings.CAPTURA_INGESTA_TOKEN
    recibido = request.headers.get('X-Captura-Token', '')
    if not esperado or not hmac.compare_digest(esperado, recibido):
        return JsonResponse({'ok': False, 'error': 'No autorizado'}, status=403)

    destinatario = request.headers.get('X-Captura-Destinatario', '')
    if not destinatario or len(request.body) > MAX_CORREO_BYTES:
        return JsonResponse({'ok': False, 'error': 'Solicitud invalida'}, status=400)

    resultado, detectado = services.procesar_correo(request.body, destinatario)
    if resultado == services.Resultado.BUZON_NO_EXISTE:
        return JsonResponse({'ok': False, 'resultado': resultado}, status=404)
    return JsonResponse({
        'ok': True,
        'resultado': resultado,
        'detectado_id': detectado.id if detectado else None,
    })


# ── Serializacion ───────────────────────────────────────────────

def _buzon_json(buzon):
    if buzon is None:
        return {'activo': False}
    return {
        'activo': True,
        'direccion': buzon.direccion,
        'verificado': buzon.verificado,
        'codigo_reenvio_gmail': buzon.codigo_reenvio_gmail,
        'enlace_reenvio_gmail': buzon.enlace_reenvio_gmail,
        'ultimo_correo_en': buzon.ultimo_correo_en.isoformat() if buzon.ultimo_correo_en else None,
    }


def _detectado_json(d, apodos=None):
    cat = d.categoria_sugerida
    apodo = (apodos or {}).get((normalizar_comercio(d.comercio), d.tipo), '')
    return {
        'id': d.id,
        'apodo': apodo,
        'banco': d.banco,
        'tipo': d.tipo,
        'operacion': d.operacion,
        'monto': str(d.monto),
        'monto_formateado': services.formatear_monto(d.monto),
        'comercio': d.comercio,
        'producto': d.producto,
        'fecha_transaccion': timezone.localtime(d.fecha_transaccion).isoformat(),
        'categoria_sugerida': {'id': cat.id, 'nombre': cat.nombre} if cat else None,
        'estado': d.estado,
        'dkim_valido': bool(d.correo and d.correo.dkim_valido),
        # Sin firma DKIM, el dominio del remitente es la unica pista de que el correo
        # no es del banco (cualquiera que conozca la direccion de captura puede escribir).
        'remitente_del_banco': bool(d.correo and remitente_es_del_banco(d.correo.remitente, d.banco)),
        'remitente': d.correo.remitente if d.correo else '',
        'leido_con_ia': d.metodo == 'IA',
        'resuelto_en': timezone.localtime(d.resuelto_en).isoformat() if d.resuelto_en else None,
    }


def _regla_json(r):
    return {
        'id': r.id,
        'comercio': r.nombre_original or r.comercio_normalizado,
        'apodo': r.apodo,
        'nombre_visible': r.nombre_visible,
        'tipo': r.tipo,
        'categoria': {'id': r.categoria_id, 'nombre': r.categoria.nombre},
        'auto_confirmar': r.auto_confirmar,
        'veces_usada': r.veces_usada,
    }


def _leer_json(request):
    try:
        return json.loads(request.body or b'{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


# ── Pagina ──────────────────────────────────────────────────────

@login_required
@ensure_csrf_cookie
def captura_view(request):
    """Pagina de captura automatica: direccion del buzon, guia y bandeja de pendientes."""
    return render(request, 'captura_bancaria/captura.html')


# ── API del usuario ─────────────────────────────────────────────

@login_required
@require_http_methods(['GET', 'POST'])
def api_buzon(request):
    """GET: estado del buzon del usuario. POST: lo activa si no existe."""
    buzon = BuzonCaptura.objects.filter(usuario=request.user, activo=True).first()
    if request.method == 'POST' and buzon is None:
        buzon, _ = BuzonCaptura.objects.get_or_create(usuario=request.user)
        if not buzon.activo:
            buzon.activo = True
            buzon.save(update_fields=['activo'])
    return JsonResponse({'ok': True, 'buzon': _buzon_json(buzon)})


@login_required
@require_POST
def api_buzon_regenerar(request):
    """Cambia el alias del buzon; la direccion anterior deja de recibir correos."""
    buzon = get_object_or_404(BuzonCaptura, usuario=request.user, activo=True)
    buzon.regenerar_alias()
    return JsonResponse({'ok': True, 'buzon': _buzon_json(buzon)})


@login_required
@require_GET
def api_resumen(request):
    """
    Estado completo de la captura del usuario: buzon, pasos de configuracion,
    estadisticas del mes y bancos soportados.
    """
    buzon = BuzonCaptura.objects.filter(usuario=request.user, activo=True).first()
    ahora = timezone.localtime()
    qs = MovimientoDetectado.objects.filter(usuario=request.user)
    pendientes = qs.filter(estado=MovimientoDetectado.Estado.PENDIENTE).aggregate(
        total=Count('id'),
        egresos=Sum('monto', filter=Q(tipo='EGRESO')),
        ingresos=Sum('monto', filter=Q(tipo='INGRESO')),
    )
    del_mes = qs.filter(fecha_transaccion__year=ahora.year, fecha_transaccion__month=ahora.month)
    confirmados_mes = del_mes.filter(estado=MovimientoDetectado.Estado.CONFIRMADO).count()
    return JsonResponse({
        'ok': True,
        'buzon': _buzon_json(buzon),
        'pasos': {
            'direccion': buzon is not None,
            'reenvio_gmail': bool(buzon and (buzon.codigo_reenvio_gmail or buzon.verificado)),
            'primera_alerta': bool(buzon and buzon.verificado),
            'reenvio_automatico': bool(buzon and buzon.reenvio_automatico_en),
        },
        'prueba': services.estado_prueba(buzon) if buzon else {'estado': 'SIN_PRUEBA'},
        'estadisticas': {
            'pendientes': pendientes['total'] or 0,
            'egresos_pendientes': services.formatear_monto(pendientes['egresos'] or 0),
            'ingresos_pendientes': services.formatear_monto(pendientes['ingresos'] or 0),
            'confirmados_mes': confirmados_mes,
            'reglas': ReglaComercio.objects.filter(usuario=request.user, activo=True).count(),
        },
        'bancos': [
            {'nombre': p.NOMBRE, 'lectura': 'IA' if getattr(p, 'USA_IA', False) else 'EXACTA'}
            for p in PARSERS
        ],
    })


@login_required
@require_http_methods(['GET', 'POST'])
def api_prueba(request):
    """
    Prueba de conexion del buzon.

    POST: genera un codigo nuevo de un solo uso (vigente 30 minutos).
    GET: estado de la prueba (ESPERANDO, RECIBIDA, VENCIDA o SIN_PRUEBA).
    """
    buzon = get_object_or_404(BuzonCaptura, usuario=request.user, activo=True)
    if request.method == 'POST':
        services.iniciar_prueba(buzon)
        buzon.refresh_from_db()
    return JsonResponse({'ok': True, 'direccion': buzon.direccion, 'prueba': services.estado_prueba(buzon)})


@login_required
@require_GET
def api_detectados(request):
    """
    Lista los movimientos detectados del usuario.

    Parametros: estado (PENDIENTE por defecto, o HISTORIAL para confirmados y
    descartados recientes) y limite (maximo 200).
    """
    estado = request.GET.get('estado', MovimientoDetectado.Estado.PENDIENTE)
    try:
        limite = max(1, min(int(request.GET.get('limite', 200)), 200))
    except ValueError:
        limite = 200

    qs = MovimientoDetectado.objects.filter(usuario=request.user).select_related('categoria_sugerida', 'correo')
    if estado == 'HISTORIAL':
        qs = qs.exclude(estado=MovimientoDetectado.Estado.PENDIENTE).order_by('-resuelto_en')
    else:
        qs = qs.filter(estado=estado)

    apodos = {
        (r.comercio_normalizado, r.tipo): r.apodo
        for r in ReglaComercio.objects.filter(usuario=request.user, activo=True).exclude(apodo='')
    }
    return JsonResponse({
        'ok': True,
        'total': qs.count(),
        'detectados': [_detectado_json(d, apodos) for d in qs[:limite]],
    })


@login_required
@require_GET
def api_reglas(request):
    """Lista las reglas de comercio que el usuario ha ido ensenando a Gastu."""
    reglas = (
        ReglaComercio.objects.filter(usuario=request.user, activo=True)
        .select_related('categoria').order_by('-fecha_creacion')
    )
    return JsonResponse({'ok': True, 'reglas': [_regla_json(r) for r in reglas]})


@login_required
@require_POST
def api_regla_crear(request):
    """
    Crea una regla antes de que llegue la alerta.
    Body JSON: {comercio, tipo, categoria_id, apodo?, auto_confirmar?}.
    Para una transferencia basta escribir la cuenta: "*5314".
    """
    datos = _leer_json(request)
    if not isinstance(datos, dict):
        return JsonResponse({'ok': False, 'error': 'Solicitud inválida'}, status=400)
    categoria = Categoria.objects.filter(pk=datos.get('categoria_id'), activo=True).first()
    try:
        regla = services.crear_regla(
            request.user, datos.get('comercio', ''), datos.get('tipo', ''), categoria,
            apodo=datos.get('apodo', ''), auto_confirmar=datos.get('auto_confirmar', False),
        )
    except services.ErrorCaptura as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
    return JsonResponse({'ok': True, 'regla': _regla_json(regla)}, status=201)


@login_required
@require_POST
def api_regla_actualizar(request, pk):
    """Edita una regla. Body JSON parcial: {auto_confirmar?, apodo?, categoria_id?}."""
    regla = get_object_or_404(ReglaComercio, pk=pk, usuario=request.user, activo=True)
    datos = _leer_json(request)
    if not isinstance(datos, dict) or not datos:
        return JsonResponse({'ok': False, 'error': 'Solicitud inválida'}, status=400)
    campos = []
    if 'auto_confirmar' in datos:
        regla.auto_confirmar = bool(datos['auto_confirmar'])
        campos.append('auto_confirmar')
    if 'apodo' in datos:
        regla.apodo = str(datos['apodo'] or '').strip()[:60]
        campos.append('apodo')
    if 'categoria_id' in datos:
        categoria = Categoria.objects.filter(pk=datos['categoria_id'], activo=True).first()
        if categoria is None or categoria.tipo != regla.tipo:
            return JsonResponse({'ok': False, 'error': 'Elige una categoría del mismo tipo.'}, status=400)
        regla.categoria = categoria
        campos.append('categoria')
    regla.save(update_fields=campos)
    return JsonResponse({'ok': True, 'regla': _regla_json(regla)})


@login_required
@require_POST
def api_regla_eliminar(request, pk):
    """Olvida una regla: el comercio vuelve a usar la sugerencia por palabras clave."""
    regla = get_object_or_404(ReglaComercio, pk=pk, usuario=request.user, activo=True)
    regla.delete()
    return JsonResponse({'ok': True, 'id': pk})


@login_required
@require_POST
def api_confirmar(request, pk):
    """Confirma un movimiento detectado. Body JSON opcional: {categoria_id, auto_confirmar}."""
    detectado = get_object_or_404(MovimientoDetectado, pk=pk, usuario=request.user)
    datos = _leer_json(request)
    if datos is None:
        return JsonResponse({'ok': False, 'error': 'Solicitud inválida'}, status=400)

    categoria = None
    if datos.get('categoria_id'):
        categoria = Categoria.objects.filter(pk=datos['categoria_id'], activo=True).first()
        if categoria is None:
            return JsonResponse({'ok': False, 'error': 'Categoría no encontrada'}, status=400)

    try:
        movimiento, advertencia = services.confirmar(
            detectado, request.user, categoria=categoria,
            auto_confirmar=datos.get('auto_confirmar'),
        )
    except services.ErrorCaptura as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
    return JsonResponse({'ok': True, 'movimiento_id': movimiento.id, 'advertencia': advertencia})


@login_required
@require_POST
def api_descartar(request, pk):
    """Descarta un movimiento detectado sin registrarlo."""
    detectado = get_object_or_404(MovimientoDetectado, pk=pk, usuario=request.user)
    try:
        services.descartar(detectado, request.user)
    except services.ErrorCaptura as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
    return JsonResponse({'ok': True, 'id': pk})


@login_required
@require_POST
def api_confirmar_lote(request):
    """Confirma varios pendientes con su categoria sugerida. Body JSON: {ids: [..]}."""
    datos = _leer_json(request)
    ids = datos.get('ids') if isinstance(datos, dict) else None
    if not isinstance(ids, list) or not ids or len(ids) > MAX_LOTE:
        return JsonResponse({'ok': False, 'error': 'Lista de movimientos inválida'}, status=400)

    confirmados, errores, advertencias = [], [], []
    for detectado in MovimientoDetectado.objects.filter(pk__in=ids, usuario=request.user):
        try:
            _, advertencia = services.confirmar(detectado, request.user)
            confirmados.append(detectado.id)
            if advertencia:
                advertencias.append(advertencia)
        except services.ErrorCaptura as exc:
            errores.append({'id': detectado.id, 'error': str(exc)})
    return JsonResponse({
        'ok': True,
        'confirmados': confirmados,
        'errores': errores,
        'advertencia': advertencias[0] if advertencias else '',
    })
