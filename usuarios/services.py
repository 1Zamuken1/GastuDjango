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


# Pool de avatares: icono Lucide sobre un color de marca (sin imagenes externas).
# La clave es lo que se guarda en Usuario.avatar.
AVATARES = {
    "ave": {"nombre": "Ave", "icono": "bird", "color": "#2563eb"},
    "gato": {"nombre": "Gato", "icono": "cat", "color": "#7c3aed"},
    "perro": {"nombre": "Perro", "icono": "dog", "color": "#b45309"},
    "pez": {"nombre": "Pez", "icono": "fish", "color": "#0e7490"},
    "conejo": {"nombre": "Conejo", "icono": "rabbit", "color": "#be185d"},
    "ardilla": {"nombre": "Ardilla", "icono": "squirrel", "color": "#c2410c"},
    "tortuga": {"nombre": "Tortuga", "icono": "turtle", "color": "#047857"},
    "cohete": {"nombre": "Cohete", "icono": "rocket", "color": "#4338ca"},
    "hoja": {"nombre": "Hoja", "icono": "leaf", "color": "#15803d"},
    "sol": {"nombre": "Sol", "icono": "sun", "color": "#a16207"},
    "luna": {"nombre": "Luna", "icono": "moon", "color": "#334155"},
    "montana": {"nombre": "Montaña", "icono": "mountain", "color": "#1e40af"},
    "cafe": {"nombre": "Café", "icono": "coffee", "color": "#78350f"},
    "gema": {"nombre": "Gema", "icono": "gem", "color": "#9333ea"},
    "estrella": {"nombre": "Estrella", "icono": "star", "color": "#b91c1c"},
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
        return {"tipo": "pool", "clave": usuario.avatar, "inicial": inicial, **elegido}
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
