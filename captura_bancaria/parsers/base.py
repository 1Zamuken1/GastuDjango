"""
Utilidades comunes para los parsers de alertas bancarias.
"""
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional


@dataclass
class DatosMovimiento:
    """Resultado de parsear una alerta bancaria."""

    banco: str
    tipo: str             # INGRESO | EGRESO
    operacion: str        # compra, transferencia, retiro, pago, abono
    monto: Decimal
    comercio: str
    fecha: Optional[datetime]
    producto: str = ''
    metodo: str = 'REGLAS'  # REGLAS | IA


RE_MONTO = re.compile(r'(?:\$|COP\s?)\s?([0-9][0-9.,]*[0-9]|[0-9])')


def parsear_monto(texto: str) -> Optional[Decimal]:
    """
    Convierte un monto en formato colombiano o anglosajon a Decimal.

    Acepta "45.000", "45.000,50", "150,000", "150,000.00" y "1234".
    Regla: si aparecen ambos separadores, el ultimo es el decimal. Si aparece
    solo uno, es decimal unicamente cuando le siguen exactamente 1 o 2 digitos.

    Args:
        texto: cadena con el numero, sin el signo de pesos.

    Returns:
        Decimal o None si no se puede interpretar.
    """
    texto = texto.strip()
    if ',' in texto and '.' in texto:
        decimal_sep = ',' if texto.rfind(',') > texto.rfind('.') else '.'
        miles_sep = '.' if decimal_sep == ',' else ','
        texto = texto.replace(miles_sep, '').replace(decimal_sep, '.')
    elif ',' in texto or '.' in texto:
        sep = ',' if ',' in texto else '.'
        partes = texto.split(sep)
        if len(partes) == 2 and 1 <= len(partes[1]) <= 2:
            texto = texto.replace(sep, '.')
        else:
            texto = texto.replace(sep, '')
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        return None
    return valor if valor > 0 else None


def primer_monto(texto: str) -> Optional[Decimal]:
    """Devuelve el primer monto precedido de $ o COP que aparezca en el texto."""
    m = RE_MONTO.search(texto)
    return parsear_monto(m.group(1)) if m else None


RE_FECHA = re.compile(r'(\d{1,2})/(\d{1,2})/(\d{2,4})')
RE_HORA = re.compile(r'\b(\d{1,2}):(\d{2})(?::\d{2})?\b')


def parsear_fecha_hora(texto: str) -> Optional[datetime]:
    """
    Extrae la primera fecha dd/mm/aaaa y la primera hora hh:mm del texto.

    Returns:
        datetime ingenuo (sin zona horaria) o None si no hay fecha.
    """
    mf = RE_FECHA.search(texto)
    if not mf:
        return None
    dia, mes, anio = (int(x) for x in mf.groups())
    if anio < 100:
        anio += 2000
    hora, minuto = 0, 0
    mh = RE_HORA.search(texto)
    if mh:
        hora, minuto = int(mh.group(1)), int(mh.group(2))
        if hora > 23 or minuto > 59:
            hora, minuto = 0, 0
    try:
        return datetime(anio, mes, dia, hora, minuto)
    except ValueError:
        return None


def normalizar_texto(texto: str) -> str:
    """Minusculas, sin tildes y con espacios simples, para comparar palabras clave."""
    sin_tildes = unicodedata.normalize('NFKD', texto)
    sin_tildes = ''.join(c for c in sin_tildes if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', sin_tildes).strip().lower()


def normalizar_comercio(comercio: str) -> str:
    """
    Clave estable para un comercio, usada por las reglas aprendidas.

    "EXITO COLOMBIA 123" y "Exito Colombia" producen "exito colombia";
    "Transferencia a cuenta *4567" produce "transferencia a cuenta cta4567".
    """
    base = normalizar_texto(comercio)
    # Conserva los sufijos de cuenta ("*4567") para distinguir destinatarios de transferencias.
    base = re.sub(r'\*\s*(\d{4})\b', r' cta\1 ', base)
    base = re.sub(r'[^a-z0-9 ]', ' ', base)
    base = re.sub(r'\b\d+\b', ' ', base)
    return re.sub(r'\s+', ' ', base).strip()[:120]
