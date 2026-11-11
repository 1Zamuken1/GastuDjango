"""
Claves para django-ratelimit.

En produccion daphne recibe todo a traves de nginx, asi que REMOTE_ADDR es siempre
la IP del contenedor nginx y un limite por IP terminaria siendo global (5 intentos
de cualquiera bloquearian el login de todos). nginx sobrescribe X-Real-IP con la IP
real del cliente; solo se confia en esa cabecera cuando la conexion viene de una
red privada o local (el proxy), nunca cuando el cliente llega directo.
"""
import ipaddress


def _es_proxy(ip: str) -> bool:
    try:
        direccion = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return direccion.is_private or direccion.is_loopback


def ip_cliente(request) -> str:
    """IP real del cliente (RATELIMIT_IP_META_KEY)."""
    remota = request.META.get('REMOTE_ADDR', '') or ''
    real = (request.META.get('HTTP_X_REAL_IP', '') or '').strip()
    if real and _es_proxy(remota):
        try:
            ipaddress.ip_address(real)
            return real
        except ValueError:
            pass
    return remota or '0.0.0.0'


def email_login(group, request) -> str:
    """Correo normalizado del POST, para limitar intentos por cuenta aunque cambie la IP."""
    return (request.POST.get('email', '') or '').strip().lower()[:254]
