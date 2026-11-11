"""
Lectura de alertas bancarias con IA (Groq), para bancos sin parser propio o
formatos que el parser de reglas no reconoce.

La IA solo extrae datos; nunca decide sola. Su resultado pasa por las mismas
validaciones y siempre queda como pendiente para que el usuario lo confirme.
"""
import json
import logging
import re
from contextvars import ContextVar
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

import requests
from django.conf import settings

from .base import DatosMovimiento

logger = logging.getLogger(__name__)

GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'
MAX_CARACTERES = 2500
OPERACIONES_VALIDAS = {'compra', 'transferencia', 'retiro', 'pago', 'abono'}

INSTRUCCIONES = (
    'Eres un extractor de datos de alertas bancarias colombianas. Recibes el texto de un correo '
    'de un banco y respondes SOLO un objeto JSON con estas claves:\n'
    '- es_movimiento: true solo si el correo informa un movimiento de dinero ya realizado '
    '(compra, pago, transferencia, retiro, abono). false para codigos, claves, publicidad, '
    'intentos rechazados o avisos sin movimiento.\n'
    '- tipo: "EGRESO" si sale dinero del usuario, "INGRESO" si entra.\n'
    '- operacion: una de compra, transferencia, retiro, pago, abono.\n'
    '- monto: numero en pesos, sin separadores de miles (ej. 45000.5).\n'
    '- comercio: comercio, persona o cuenta contraparte, maximo 60 caracteres. Si es una cuenta, '
    'solo los ultimos 4 digitos con asterisco (ej. "Transferencia a cuenta *4567").\n'
    '- fecha: "AAAA-MM-DD HH:MM" o null si no aparece.\n'
    '- producto: producto del usuario con solo los ultimos 4 digitos (ej. "T.Cred *1234") o "".\n'
    'No inventes datos: si algo no aparece en el texto, usa null o "".'
)


# Quien procesa el correo puede fijar aqui una funcion que autoriza (y descuenta)
# cada llamada a la IA. Se consulta solo cuando de verdad se va a llamar a Groq,
# para no gastar cupo en correos que el parser de reglas ya entiende.
autorizador_ia: ContextVar = ContextVar('autorizador_ia', default=None)


def ia_disponible() -> bool:
    """True si hay clave de Groq y la lectura con IA esta habilitada."""
    return bool(getattr(settings, 'GROQ_API_KEY', None)) and getattr(settings, 'CAPTURA_USAR_IA', True)


def _llamar_groq(asunto: str, texto: str) -> dict:
    """Pide a Groq la extraccion en JSON. Lanza excepcion si falla la llamada."""
    modelo = (
        getattr(settings, 'GROQ_MODEL_CAPTURA', None)
        or getattr(settings, 'GROQ_MODEL', None)
        or 'openai/gpt-oss-120b'
    )
    # gpt-oss razona antes de responder; con esfuerzo bajo no se come el max_tokens.
    extra = {'reasoning_effort': 'low'} if modelo.startswith('openai/gpt-oss') else {}
    respuesta = requests.post(
        GROQ_API_URL,
        headers={'Authorization': f'Bearer {settings.GROQ_API_KEY}', 'Content-Type': 'application/json'},
        json={
            'model': modelo,
            'temperature': 0,
            'max_tokens': 800,
            'response_format': {'type': 'json_object'},
            **extra,
            'messages': [
                {'role': 'system', 'content': INSTRUCCIONES},
                {'role': 'user', 'content': f'Asunto: {asunto}\n\n{texto[:MAX_CARACTERES]}'},
            ],
        },
        timeout=20,
    )
    respuesta.raise_for_status()
    contenido = respuesta.json()['choices'][0]['message']['content']
    return json.loads(contenido)


def _digitos(texto: str) -> str:
    return re.sub(r'\D', '', texto)


def _monto_aparece_en_texto(monto: Decimal, texto: str) -> bool:
    """Evita montos inventados: la parte entera debe aparecer tal cual entre los digitos del texto."""
    entero = str(int(monto))
    return entero in _digitos(texto)


def validar_respuesta(datos: dict, banco: str, texto: str) -> Optional[DatosMovimiento]:
    """
    Convierte la respuesta de la IA en DatosMovimiento, o None si no es confiable.

    Rechaza respuestas sin movimiento, con tipo u operacion invalidos o con un
    monto que no aparece en el texto original.
    """
    if not isinstance(datos, dict) or not datos.get('es_movimiento'):
        return None
    tipo = str(datos.get('tipo', '')).upper()
    operacion = str(datos.get('operacion', '')).lower()
    if tipo not in ('INGRESO', 'EGRESO') or operacion not in OPERACIONES_VALIDAS:
        return None
    try:
        monto = Decimal(str(datos.get('monto'))).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if monto <= 0 or not _monto_aparece_en_texto(monto, texto):
        return None

    fecha = None
    if datos.get('fecha'):
        try:
            fecha = datetime.strptime(str(datos['fecha'])[:16], '%Y-%m-%d %H:%M')
        except ValueError:
            fecha = None

    comercio = str(datos.get('comercio') or '').strip()[:120] or f'{operacion.capitalize()} {banco}'
    producto = str(datos.get('producto') or '').strip()[:40]
    return DatosMovimiento(
        banco=banco, tipo=tipo, operacion=operacion, monto=monto,
        comercio=comercio, fecha=fecha, producto=producto, metodo='IA',
    )


def parsear_con_ia(banco: str, asunto: str, texto: str) -> Optional[DatosMovimiento]:
    """
    Extrae un movimiento con IA. Devuelve None si la IA no esta disponible,
    falla o su respuesta no pasa las validaciones.
    """
    if not ia_disponible() or not texto.strip():
        return None
    autorizar = autorizador_ia.get()
    if autorizar is not None and not autorizar():
        logger.info('Lectura con IA omitida para %s: cupo agotado', banco)
        return None
    try:
        datos = _llamar_groq(asunto, texto)
    except Exception as exc:
        logger.warning('Lectura con IA fallo para %s: %s', banco, exc)
        return None
    return validar_respuesta(datos, banco, texto)
