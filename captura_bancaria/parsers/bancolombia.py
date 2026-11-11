"""
Parser de alertas de Bancolombia.

IMPORTANTE: los patrones estan escritos sobre formatos aproximados de las alertas
(compra, transferencia enviada y recibida, pago, retiro, abono). Hay que ajustarlos
con correos reales en captura_bancaria/tests/correos/ antes de ir a produccion.
"""
import re
from typing import Optional

from .base import DatosMovimiento, RE_MONTO, normalizar_texto, parsear_fecha_hora, parsear_monto
from .ia import parsear_con_ia

NOMBRE = 'Bancolombia'
DOMINIOS = ('bancolombia.com.co', 'notificacionesbancolombia.com', 'bancolombia.com')

# El orden importa: "Recibiste una transferencia" debe ganar sobre "transferencia".
OPERACIONES = [
    ('INGRESO', 'transferencia', ('recibiste', 'te transfirieron', 'recibio una transferencia')),
    ('INGRESO', 'abono', ('abono', 'consignacion', 'deposito', 'te consignaron')),
    ('EGRESO', 'compra', ('compraste', 'compra por', 'compra de', 'le informa compra')),
    ('EGRESO', 'retiro', ('retiraste', 'retiro por', 'retiro de')),
    ('EGRESO', 'pago', ('pagaste', 'pago por', 'pago de', 'pago a')),
    ('EGRESO', 'transferencia', ('transferiste', 'transferencia por', 'transferencia de', 'enviaste')),
]

# Alertas que mencionan dinero pero no son movimientos.
IGNORAR = ('clave dinamica', 'codigo de verificacion', 'inicio de sesion', 'intento fallido', 'rechazad')

FIN_COMERCIO = r'(?=\s+\d{1,2}:\d{2}|\s+con\s+tu|\s+desde|\s+en\s+tu|\s+a\s+tu|\s+el\s+\d|\s+\d{1,2}/\d{1,2}/|,|\.\s|\.$|$)'
RE_COMERCIO_EN = re.compile(r'\ben\s+(.+?)' + FIN_COMERCIO, re.IGNORECASE)
RE_COMERCIO_A = re.compile(r'\ba\s+(?:la\s+|el\s+)?(.+?)' + FIN_COMERCIO, re.IGNORECASE)
RE_COMERCIO_DE = re.compile(r'\bde\s+(.+?)' + FIN_COMERCIO, re.IGNORECASE)
RE_PRODUCTO = re.compile(
    r'(T\.?\s?Cred|T\.?\s?Deb|tarjeta|cuenta(?:\s+de)?(?:\s+ahorros|\s+corriente)?)\s*\*?\s*(\d{4})\b',
    re.IGNORECASE,
)

RE_CONCEPTO_ABONO = re.compile(r'\babono\s+(?:de|por)\s+([a-zA-Z ]{3,40}?)\s+(?:por|en|\$)', re.IGNORECASE)

# La frase de la alerta empieza con "Bancolombia:" o "Bancolombia le informa". El resto del
# correo (logo, publicidad, enlaces) se descarta para que no contamine el comercio.
RE_ALERTA = re.compile(
    r'Bancolombia(?:\s*:|\s+le\s+informa)\s*(.+?)(?=¿\s*Dudas|Inquietudes|Estamos cerca|$)',
    re.IGNORECASE | re.DOTALL,
)
RE_CUENTA_DESTINO = re.compile(r'\ba\s+(?:la\s+)?cuenta\s*\*?\s*(\d{4,})', re.IGNORECASE)

NO_ES_COMERCIO = ('tu ', 'su ', 'cuenta', 'tarjeta', 'la cuenta', 't.cred', 't.deb')


def es_remitente(remitente: str, texto: str) -> bool:
    """
    Indica si el correo viene de Bancolombia.

    Acepta el dominio del remitente o, para correos reenviados a mano, que el
    texto empiece mencionando al banco.
    """
    remitente = remitente.lower()
    if any(d in remitente for d in DOMINIOS):
        return True
    return normalizar_texto(texto[:300]).find('bancolombia') != -1


def _clasificar(texto_norm: str):
    for tipo, operacion, claves in OPERACIONES:
        if any(c in texto_norm for c in claves):
            return tipo, operacion
    return None, None


def _limpiar_comercio(valor: str) -> str:
    valor = re.sub(r'\s+', ' ', valor).strip(' .,:;')
    if not valor or valor.lower().startswith(NO_ES_COMERCIO) or RE_MONTO.match(valor):
        return ''
    return valor[:120]


def _extraer_comercio(resto: str, tipo: str, operacion: str) -> str:
    if tipo == 'INGRESO':
        patrones = (RE_COMERCIO_DE,)
    elif operacion in ('pago', 'transferencia'):
        patrones = (RE_COMERCIO_A, RE_COMERCIO_EN)
    else:
        patrones = (RE_COMERCIO_EN,)
    for patron in patrones:
        m = patron.search(resto)
        if m:
            comercio = _limpiar_comercio(m.group(1))
            if comercio:
                return comercio
    return ''


def parsear(asunto: str, texto: str) -> Optional[DatosMovimiento]:
    """
    Extrae un movimiento de una alerta de Bancolombia.

    Args:
        asunto: asunto del correo.
        texto: cuerpo en texto plano.

    Returns:
        DatosMovimiento o None si el correo no describe un movimiento.
    """
    m_alerta = RE_ALERTA.search(texto)
    if m_alerta:
        texto = m_alerta.group(1).strip()
    contenido = f'{asunto}\n{texto}'
    norm = normalizar_texto(contenido)
    if any(i in norm for i in IGNORAR):
        return None

    tipo, operacion = _clasificar(norm)
    fuente = texto if RE_MONTO.search(texto) else asunto
    m_monto = RE_MONTO.search(fuente)
    monto = parsear_monto(m_monto.group(1)) if m_monto else None
    if not tipo or monto is None:
        # Formato que las reglas no conocen: se intenta leer con IA.
        return parsear_con_ia(NOMBRE, asunto, texto)

    resto = fuente[m_monto.end():]
    comercio = _extraer_comercio(resto, tipo, operacion)
    if not comercio and tipo == 'EGRESO' and operacion == 'transferencia':
        m_destino = RE_CUENTA_DESTINO.search(resto)
        if m_destino:
            comercio = f'Transferencia a cuenta *{m_destino.group(1)[-4:]}'
    if not comercio and operacion == 'abono':
        m_concepto = RE_CONCEPTO_ABONO.search(texto)
        if m_concepto:
            comercio = f'Abono de {m_concepto.group(1).strip().lower()}'
    if not comercio:
        comercio = f'{operacion.capitalize()} {NOMBRE}'

    producto = ''
    mp = RE_PRODUCTO.search(texto)
    if mp:
        producto = f'{mp.group(1)} *{mp.group(2)}'

    return DatosMovimiento(
        banco=NOMBRE,
        tipo=tipo,
        operacion=operacion,
        monto=monto,
        comercio=comercio,
        fecha=parsear_fecha_hora(texto) or parsear_fecha_hora(asunto),
        producto=producto,
    )
