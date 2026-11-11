"""Servicios de usuarios."""
from urllib.parse import urlparse

from django.templatetags.static import static

from .avatares_gastu import VARIANTES


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


# Pool de avatares: variantes de Gastu, la mascota (SVG propios en
# usuarios/static/usuarios/img/avatares/, generados por usuarios/avatares_gastu.py).
# La clave es lo que se guarda en Usuario.avatar.
AVATARES = {
    clave: {"nombre": nombre, "imagen": f"usuarios/img/avatares/gastu_{clave}.svg", "color": fondo}
    for clave, (nombre, fondo, *_resto) in VARIANTES.items()
}


def avatar_de(usuario) -> dict:
    """
    Como se muestra el avatar del usuario.

    Prioridad: el avatar elegido del pool; si no eligio (automatico), la foto de
    Google; si tampoco hay, la inicial del nombre.
    """
    inicial = (usuario.username or usuario.email or "?")[:1].upper()
    elegido = AVATARES.get(usuario.avatar or "")
    if elegido:
        return {"tipo": "pool", "clave": usuario.avatar, "inicial": inicial,
                "url": static(elegido["imagen"]), **elegido}
    foto = foto_de_perfil(usuario)
    if foto:
        return {"tipo": "foto", "clave": "", "inicial": inicial, "url": foto}
    return {"tipo": "inicial", "clave": "", "inicial": inicial}


def cambiar_avatar(usuario, clave: str) -> dict:
    """
    Guarda el avatar elegido. "" vuelve al modo automatico.
    Lanza ValueError si la clave no esta en el pool.
    """
    clave = (clave or "").strip()
    if clave and clave not in AVATARES:
        raise ValueError("Avatar no válido.")
    usuario.avatar = clave
    usuario.save(update_fields=["avatar"])
    return avatar_de(usuario)
