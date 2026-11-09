"""
Logica de negocio de la captura bancaria por correo reenviado.

Flujo: procesar_correo() -> MovimientoDetectado (PENDIENTE) -> confirmar() -> Movimiento.
"""
import hashlib
import logging
import re
from datetime import timedelta
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parseaddr

from django.db import IntegrityError, transaction
from django.utils import timezone

from categorias.models import Categoria
from movimientos.models import Movimiento

from .models import BuzonCaptura, CorreoEntrante, MovimientoDetectado, ReglaComercio
from .parsers import detectar_parser
from .parsers.base import normalizar_comercio, normalizar_texto

logger = logging.getLogger(__name__)

MAX_TEXTO = 20000
REMITENTE_VERIFICACION_GMAIL = 'forwarding-noreply@google.com'
RE_CODIGO_GMAIL = re.compile(r'(?:c[oó]digo de confirmaci[oó]n|confirmation code)\s*:?\s*(\d{6,12})', re.IGNORECASE)
RE_ENLACE_GMAIL = re.compile(r'https://mail(?:-settings)?\.google\.com/mail/\S+')


class Resultado:
    """Codigos que devuelve procesar_correo, usados por la ingesta para responder al SMTP."""

    DETECTADO = 'DETECTADO'
    AUTO_CONFIRMADO = 'AUTO_CONFIRMADO'
    VERIFICACION_GMAIL = 'VERIFICACION_GMAIL'
    IGNORADO = 'IGNORADO'
    DUPLICADO = 'DUPLICADO'
    BUZON_NO_EXISTE = 'BUZON_NO_EXISTE'


# ── Lectura del correo ──────────────────────────────────────────

def leer_correo(raw: bytes) -> EmailMessage:
    """Parsea los bytes del correo con la politica moderna de la libreria email."""
    return BytesParser(policy=policy.default).parsebytes(raw)


def extraer_texto(msg: EmailMessage) -> str:
    """
    Devuelve el cuerpo del correo como texto plano.

    Prefiere la parte text/plain; si solo hay HTML, lo convierte a texto con lxml.
    """
    parte = msg.get_body(preferencelist=('plain', 'html'))
    if parte is None:
        return ''
    try:
        contenido = parte.get_content()
    except (LookupError, UnicodeDecodeError):
        contenido = parte.get_payload(decode=True).decode('utf-8', errors='replace')
    if parte.get_content_subtype() == 'html':
        from lxml import html as lxml_html
        try:
            contenido = lxml_html.fromstring(contenido).text_content()
        except Exception:
            contenido = re.sub(r'<[^>]+>', ' ', contenido)
    return re.sub(r'[ \t\r\f\v]+', ' ', contenido).strip()[:MAX_TEXTO]


def alias_desde_destinatario(destinatario: str) -> str:
    """Extrae el alias (parte local, sin etiquetas +algo) de una direccion de destino."""
    direccion = parseaddr(destinatario)[1] or destinatario
    local = direccion.split('@')[0]
    return local.split('+')[0].strip().lower()


def verificar_dkim(raw: bytes, dominios) -> bool:
    """
    Verifica que el correo tenga una firma DKIM valida de alguno de los dominios dados.

    Revisa todas las firmas, porque al reenviar Gmail puede agregar la suya.
    Cualquier error (sin firma, DNS caido) se trata como firma no valida.
    """
    try:
        import dkim
    except ImportError:
        return False
    try:
        verificador = dkim.DKIM(raw)
        firmas = [v for k, v in verificador.headers if k.lower() == b'dkim-signature']
        for idx, firma in enumerate(firmas):
            m = re.search(rb'\bd=([^;\s]+)', firma)
            if not m:
                continue
            dominio = m.group(1).decode('ascii', errors='ignore').lower()
            if not any(dominio == d or dominio.endswith('.' + d) for d in dominios):
                continue
            if verificador.verify(idx=idx):
                return True
    except Exception as exc:
        logger.info('DKIM no verificable: %s', exc)
    return False


# ── Categorias ──────────────────────────────────────────────────

PALABRAS_CATEGORIA = {
    'EGRESO': [
        ('alimentacion', ('exito', 'carulla', 'jumbo', 'd1', 'ara', 'olimpica', 'makro', 'rappi',
                          'ifood', 'restaurante', 'panaderia', 'supermercado', 'mercado',
                          'frisby', 'kfc', 'mcdonalds', 'el corral', 'crepes', 'juan valdez')),
        ('transporte', ('uber', 'didi', 'cabify', 'indriver', 'terpel', 'primax', 'texaco', 'esso',
                        'peaje', 'transmilenio', 'metro', 'gasolina', 'parqueadero', 'mio')),
        ('entretenimiento', ('netflix', 'spotify', 'disney', 'hbo', 'max', 'prime video',
                             'cine colombia', 'cinemark', 'procinal', 'steam', 'playstation', 'xbox')),
        ('vivienda', ('arriendo', 'epm', 'codensa', 'enel', 'vanti', 'acueducto', 'gas natural',
                      'claro', 'movistar', 'tigo', 'etb', 'administracion')),
        ('salud', ('drogueria', 'farmacia', 'cruz verde', 'colsubsidio', 'la rebaja', 'farmatodo',
                   'clinica', 'hospital', 'eps', 'odontolog')),
        ('educacion', ('universidad', 'colegio', 'platzi', 'coursera', 'udemy', 'sena', 'libreria')),
        ('tecnologia', ('apple', 'google', 'microsoft', 'ktronix', 'alkosto', 'openai')),
        ('ropa y calzado', ('zara', 'arturo calle', 'koaj', 'adidas', 'nike', 'studio f', 'tennis')),
        ('deudas y creditos', ('credito', 'prestamo', 'cuota', 'abono a tarjeta')),
    ],
    'INGRESO': [
        ('salario', ('nomina', 'salario', 'sueldo')),
        ('reembolsos', ('reembolso', 'devolucion', 'reverso')),
        ('transferencias', ('transferencia',)),
    ],
}
CATEGORIA_POR_DEFECTO = {'EGRESO': 'otros gastos', 'INGRESO': 'otros ingresos'}


def _categoria_por_nombre(tipo: str, nombre_normalizado: str):
    """Busca una categoria activa comparando el nombre sin tildes ni mayusculas."""
    for cat in Categoria.objects.filter(tipo=tipo, activo=True):
        if normalizar_texto(cat.nombre) == nombre_normalizado:
            return cat
    return None


def sugerir_categoria(usuario, tipo: str, comercio: str, operacion: str):
    """
    Sugiere la categoria de un movimiento detectado.

    Orden: regla aprendida del usuario, palabras clave del comercio u operacion,
    y por ultimo la categoria "Otros" del tipo.

    Returns:
        tupla (Categoria o None, ReglaComercio o None).
    """
    clave = normalizar_comercio(comercio)
    regla = ReglaComercio.objects.filter(
        usuario=usuario, comercio_normalizado=clave, tipo=tipo, activo=True,
    ).select_related('categoria').first()
    if regla:
        return regla.categoria, regla

    texto = f' {clave} {normalizar_texto(operacion)} '
    for nombre_cat, palabras in PALABRAS_CATEGORIA.get(tipo, []):
        if any(re.search(rf'\b{re.escape(p)}\b', texto) for p in palabras):
            cat = _categoria_por_nombre(tipo, nombre_cat)
            if cat:
                return cat, None
    return _categoria_por_nombre(tipo, CATEGORIA_POR_DEFECTO[tipo]), None


# ── Procesamiento ───────────────────────────────────────────────

def _fecha_transaccion(fecha_naive):
    """Convierte la fecha del banco a hora de Colombia; si falta o es absurda, usa ahora."""
    ahora = timezone.now()
    if fecha_naive is None:
        return ahora
    fecha = timezone.make_aware(fecha_naive, timezone.get_current_timezone())
    if fecha > ahora + timedelta(days=1) or fecha < ahora - timedelta(days=365):
        return ahora
    return fecha


def calcular_hash(usuario_id, datos, fecha) -> str:
    """Huella del movimiento para no registrar dos veces la misma alerta."""
    base = '|'.join([
        str(usuario_id), datos.banco, datos.tipo, f'{datos.monto:.2f}',
        fecha.strftime('%Y%m%d%H%M'), normalizar_comercio(datos.comercio), datos.producto,
    ])
    return hashlib.sha256(base.encode('utf-8')).hexdigest()


def _procesar_verificacion_gmail(buzon, texto):
    m_codigo = RE_CODIGO_GMAIL.search(texto)
    m_enlace = RE_ENLACE_GMAIL.search(texto)
    buzon.codigo_reenvio_gmail = m_codigo.group(1) if m_codigo else ''
    buzon.enlace_reenvio_gmail = m_enlace.group(0)[:500] if m_enlace else ''
    buzon.save(update_fields=['codigo_reenvio_gmail', 'enlace_reenvio_gmail'])


def procesar_correo(raw: bytes, destinatario: str):
    """
    Procesa un correo recibido en un buzon de captura.

    Args:
        raw: bytes completos del correo (cabeceras y cuerpo).
        destinatario: direccion de destino del sobre SMTP (alias@dominio).

    Returns:
        tupla (codigo de Resultado, MovimientoDetectado o None).
    """
    alias = alias_desde_destinatario(destinatario)
    buzon = BuzonCaptura.objects.filter(alias=alias, activo=True).select_related('usuario').first()
    if buzon is None:
        return Resultado.BUZON_NO_EXISTE, None

    msg = leer_correo(raw)
    remitente = parseaddr(str(msg.get('From', '')))[1].lower()
    asunto = str(msg.get('Subject', ''))[:255]
    message_id = str(msg.get('Message-ID', '')).strip()[:255]
    texto = extraer_texto(msg)

    BuzonCaptura.objects.filter(pk=buzon.pk).update(ultimo_correo_en=timezone.now())

    if message_id and CorreoEntrante.objects.filter(buzon=buzon, message_id=message_id).exists():
        return Resultado.DUPLICADO, None

    correo = CorreoEntrante(
        buzon=buzon, message_id=message_id, remitente=remitente[:255],
        asunto=asunto, texto=texto,
    )

    if remitente == REMITENTE_VERIFICACION_GMAIL:
        _procesar_verificacion_gmail(buzon, texto)
        correo.estado = CorreoEntrante.Estado.PROCESADO
        correo.detalle = 'Verificacion de reenvio de Gmail'
        correo.save()
        return Resultado.VERIFICACION_GMAIL, None

    parser = detectar_parser(remitente, texto)
    if parser is None:
        correo.estado = CorreoEntrante.Estado.IGNORADO
        correo.detalle = 'Remitente no corresponde a un banco soportado'
        correo.save()
        return Resultado.IGNORADO, None

    correo.dkim_valido = verificar_dkim(raw, parser.DOMINIOS)
    try:
        datos = parser.parsear(asunto, texto)
    except Exception as exc:
        logger.exception('Error parseando correo de %s', remitente)
        correo.estado = CorreoEntrante.Estado.ERROR
        correo.detalle = f'Error del parser: {exc}'[:255]
        correo.save()
        return Resultado.IGNORADO, None

    if datos is None:
        correo.estado = CorreoEntrante.Estado.IGNORADO
        correo.detalle = f'Correo de {parser.NOMBRE} sin movimiento reconocible'
        correo.save()
        return Resultado.IGNORADO, None

    correo.estado = CorreoEntrante.Estado.PROCESADO
    correo.save()

    if not buzon.verificado:
        BuzonCaptura.objects.filter(pk=buzon.pk).update(verificado=True)

    usuario = buzon.usuario
    fecha = _fecha_transaccion(datos.fecha)
    categoria, regla = sugerir_categoria(usuario, datos.tipo, datos.comercio, datos.operacion)

    try:
        with transaction.atomic():
            detectado = MovimientoDetectado.objects.create(
                usuario=usuario, correo=correo, banco=datos.banco, tipo=datos.tipo,
                operacion=datos.operacion, monto=datos.monto, comercio=datos.comercio,
                fecha_transaccion=fecha, producto=datos.producto,
                categoria_sugerida=categoria, metodo=datos.metodo,
                hash_unico=calcular_hash(usuario.id, datos, fecha),
            )
    except IntegrityError:
        correo.estado = CorreoEntrante.Estado.IGNORADO
        correo.detalle = 'Movimiento ya detectado antes'
        correo.save(update_fields=['estado', 'detalle'])
        return Resultado.DUPLICADO, None

    if regla and regla.auto_confirmar and correo.dkim_valido and categoria:
        confirmar(detectado, usuario)
        return Resultado.AUTO_CONFIRMADO, detectado

    notificar_detectado(detectado)
    return Resultado.DETECTADO, detectado


# ── Notificacion ────────────────────────────────────────────────

def formatear_monto(monto) -> str:
    """Formatea un monto en pesos colombianos: 45000 -> $45.000."""
    entero = f'{int(round(monto)):,}'.replace(',', '.')
    return f'${entero}'


def notificar_detectado(detectado):
    """Crea la notificacion del movimiento detectado y la envia por WebSocket."""
    from notificaciones.dispatcher import NotificationDispatcher
    from notificaciones.models import Notificacion

    es_egreso = detectado.tipo == MovimientoDetectado.Tipo.EGRESO
    verbo = 'Egreso' if es_egreso else 'Ingreso'
    sugerida = detectado.categoria_sugerida.nombre if detectado.categoria_sugerida else 'sin categoría'
    notif = Notificacion.objects.create(
        usuario=detectado.usuario,
        tipo=Notificacion.Tipo.MOVIMIENTO_DETECTADO,
        titulo=f'{verbo} detectado: {formatear_monto(detectado.monto)}'[:100],
        descripcion=(
            f'{detectado.comercio} - {detectado.banco}. '
            f'Categoría sugerida: {sugerida}. Revísalo en Captura automática para confirmarlo.'
        ),
        modulo=Notificacion.Modulo.EGRESOS if es_egreso else Notificacion.Modulo.INGRESOS,
        referencia_id=detectado.id,
        referencia_tipo='detectado',
    )
    # En segundo plano: si el channel layer tarda o falla, la ingesta no debe esperar.
    NotificationDispatcher._executor.submit(
        NotificationDispatcher._push_to_websocket, detectado.usuario_id, [notif],
    )


# ── Confirmacion ────────────────────────────────────────────────

class ErrorCaptura(Exception):
    """Error de negocio al confirmar o descartar un movimiento detectado."""


def _advertencia_disponible(detectado):
    from dashboard.models import ResumenMensual

    if detectado.tipo != MovimientoDetectado.Tipo.EGRESO:
        return ''
    fecha = timezone.localtime(detectado.fecha_transaccion)
    resumen = ResumenMensual.objects.filter(
        usuario=detectado.usuario, mes=fecha.month, anio=fecha.year,
    ).first()
    disponible = resumen.disponible if resumen else 0
    if detectado.monto > disponible:
        return 'Este egreso supera tu disponible del mes. Lo registramos igual porque el gasto ya ocurrió.'
    return ''


def confirmar(detectado, usuario, categoria=None, auto_confirmar=None):
    """
    Convierte un movimiento detectado en un Movimiento real.

    Los egresos que superan el disponible se registran igual (el gasto ya ocurrio)
    y se devuelve una advertencia. La categoria elegida se guarda como regla para
    el comercio.

    Args:
        detectado: MovimientoDetectado en estado PENDIENTE del usuario.
        usuario: usuario autenticado (dueno del detectado).
        categoria: Categoria elegida; si es None se usa la sugerida.
        auto_confirmar: si se indica, actualiza la regla del comercio.

    Returns:
        tupla (Movimiento, advertencia str).

    Raises:
        ErrorCaptura: si ya fue resuelto, no tiene categoria o el tipo no coincide.
    """
    if detectado.usuario_id != usuario.id:
        raise ErrorCaptura('Movimiento no encontrado.')
    categoria = categoria or detectado.categoria_sugerida
    if categoria is None:
        raise ErrorCaptura('Elige una categoría para registrar el movimiento.')
    if categoria.tipo != detectado.tipo:
        raise ErrorCaptura('La categoría no corresponde al tipo de movimiento.')

    with transaction.atomic():
        bloqueado = MovimientoDetectado.objects.select_for_update().get(pk=detectado.pk)
        if bloqueado.estado != MovimientoDetectado.Estado.PENDIENTE:
            raise ErrorCaptura('Este movimiento ya fue revisado.')

        advertencia = _advertencia_disponible(bloqueado)
        descripcion = f'{bloqueado.comercio} ({bloqueado.banco})'
        movimiento = Movimiento.objects.create(
            usuario=usuario, categoria=categoria, tipo=bloqueado.tipo,
            monto=bloqueado.monto, descripcion=descripcion[:255],
            fecha_registro=bloqueado.fecha_transaccion,
        )
        bloqueado.estado = MovimientoDetectado.Estado.CONFIRMADO
        bloqueado.movimiento = movimiento
        bloqueado.categoria_sugerida = categoria
        bloqueado.resuelto_en = timezone.now()
        bloqueado.save(update_fields=['estado', 'movimiento', 'categoria_sugerida', 'resuelto_en'])

        _aprender_regla(bloqueado, categoria, auto_confirmar)

    detectado.refresh_from_db()
    _marcar_notificacion_leida(detectado)
    return movimiento, advertencia


def _aprender_regla(detectado, categoria, auto_confirmar):
    clave = normalizar_comercio(detectado.comercio)
    if not clave:
        return
    regla, _ = ReglaComercio.objects.get_or_create(
        usuario=detectado.usuario, comercio_normalizado=clave, tipo=detectado.tipo,
        defaults={'categoria': categoria},
    )
    regla.categoria = categoria
    regla.veces_usada += 1
    if auto_confirmar is not None:
        regla.auto_confirmar = bool(auto_confirmar)
    regla.save()


def descartar(detectado, usuario):
    """Marca un movimiento detectado como descartado (no crea Movimiento)."""
    if detectado.usuario_id != usuario.id:
        raise ErrorCaptura('Movimiento no encontrado.')
    actualizados = MovimientoDetectado.objects.filter(
        pk=detectado.pk, estado=MovimientoDetectado.Estado.PENDIENTE,
    ).update(estado=MovimientoDetectado.Estado.DESCARTADO, resuelto_en=timezone.now())
    if not actualizados:
        raise ErrorCaptura('Este movimiento ya fue revisado.')
    _marcar_notificacion_leida(detectado)


def _marcar_notificacion_leida(detectado):
    from notificaciones.models import Notificacion

    Notificacion.objects.filter(
        usuario=detectado.usuario, tipo=Notificacion.Tipo.MOVIMIENTO_DETECTADO,
        referencia_id=detectado.id,
    ).update(leida=True)


def purgar_textos_antiguos(dias=30):
    """Borra el texto de los correos con mas de `dias` dias. Devuelve cuantos se limpiaron."""
    limite = timezone.now() - timedelta(days=dias)
    return CorreoEntrante.objects.filter(recibido_en__lt=limite).exclude(texto='').update(texto='')
