"""
Registro de parsers de alertas bancarias.

- Bancos con parser de reglas propio (rapido y sin costo): parsers/<banco>.py con
  NOMBRE, DOMINIOS, es_remitente() y parsear(). Si las reglas no reconocen el
  formato, el propio parser intenta leerlo con IA.
- Resto de bancos conocidos: parsers/generico.py, que los identifica por dominio
  y lee el correo con IA.
"""
from typing import Optional

from . import bancolombia
from .base import DatosMovimiento
from .generico import PARSERS_GENERICOS

PARSERS = [bancolombia, *PARSERS_GENERICOS]


def bancos_soportados():
    """Nombres de los bancos que Gastu reconoce, para mostrarlos al usuario."""
    return [p.NOMBRE for p in PARSERS]


def detectar_parser(remitente: str, texto: str):
    """Devuelve el parser del banco que envio el correo, o None."""
    for parser in PARSERS:
        if parser.es_remitente(remitente, texto):
            return parser
    return None


def parsear_correo(remitente: str, asunto: str, texto: str) -> Optional[DatosMovimiento]:
    """
    Intenta extraer un movimiento con el parser del banco correspondiente.

    Returns:
        DatosMovimiento o None si el banco no esta soportado o no es un movimiento.
    """
    parser = detectar_parser(remitente, texto)
    if parser is None:
        return None
    return parser.parsear(asunto, texto)
