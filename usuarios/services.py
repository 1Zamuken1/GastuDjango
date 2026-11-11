"""Servicios de usuarios."""
from urllib.parse import urlparse


def foto_de_perfil(usuario) -> str:
    """
    URL de la foto de Google del usuario, o "" si no tiene.

    Solo se acepta https y el dominio de fotos de Google (*.googleusercontent.com),
    que es el que permite la CSP (img-src); cualquier otro valor se descarta.
    """
    cuenta = usuario.socialaccount_set.filter(provider="google").first()
    if cuenta is None:
        return ""
    url = str((cuenta.extra_data or {}).get("picture") or "")
    partes = urlparse(url)
    if partes.scheme != "https" or not (partes.hostname or "").endswith(".googleusercontent.com"):
        return ""
    return url
