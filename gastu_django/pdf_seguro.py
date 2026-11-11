"""
Utilidades para generar PDF con xhtml2pdf sin abrir la puerta a SSRF.

xhtml2pdf descarga cualquier URL http(s) y lee cualquier ruta local que aparezca
en un src. Por eso:
- imagen_png_segura: solo acepta graficas enviadas como data URI PNG en base64.
- link_callback_seguro: solo deja pasar data URIs y archivos de las carpetas de
  estaticos; cualquier otro recurso se reemplaza por un data URI vacio.
"""
import base64
import binascii
import os
import re

from django.conf import settings

MAX_IMAGEN_BYTES = 3 * 1024 * 1024
RE_DATA_PNG = re.compile(r'^data:image/png;base64,([A-Za-z0-9+/=\s]+)$')
FIRMA_PNG = b'\x89PNG\r\n\x1a\n'
RECURSO_VACIO = 'data:,'


def imagen_png_segura(valor) -> str:
    """Devuelve el data URI si es un PNG valido en base64; si no, cadena vacia."""
    valor = (valor or '').strip()
    if not valor or len(valor) > MAX_IMAGEN_BYTES * 4 // 3 + 64:
        return ''
    m = RE_DATA_PNG.match(valor)
    if not m:
        return ''
    try:
        cabecera = base64.b64decode(m.group(1)[:24], validate=False)
    except (binascii.Error, ValueError):
        return ''
    return valor if cabecera.startswith(FIRMA_PNG) else ''


def _carpetas_estaticas():
    carpetas = [str(d) for d in getattr(settings, 'STATICFILES_DIRS', [])]
    if getattr(settings, 'STATIC_ROOT', None):
        carpetas.append(str(settings.STATIC_ROOT))
    return [os.path.realpath(c) for c in carpetas]


def link_callback_seguro(uri, rel=None):
    """Resuelve los recursos de un PDF permitiendo solo data URIs y estaticos locales."""
    uri = str(uri or '')
    if uri.startswith('data:'):
        return uri
    if '://' in uri or uri.startswith('//'):
        return RECURSO_VACIO
    ruta = os.path.realpath(uri)
    for carpeta in _carpetas_estaticas():
        if ruta == carpeta or ruta.startswith(carpeta + os.sep):
            return ruta if os.path.isfile(ruta) else RECURSO_VACIO
    return RECURSO_VACIO
