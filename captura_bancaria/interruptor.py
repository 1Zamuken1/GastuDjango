"""
Interruptor de la captura automatica (settings.CAPTURA_HABILITADA).

Con la captura apagada, el modulo desaparece de la app: no sale en el menu ni
en el panel de notificaciones, y todas sus rutas (incluida la ingesta de
correos) responden 404. Se lee en cada peticion para que override_settings
funcione en los tests.
"""
from functools import wraps

from django.conf import settings
from django.http import Http404


def captura_habilitada() -> bool:
    return bool(getattr(settings, 'CAPTURA_HABILITADA', False))


def requiere_captura(vista):
    """Decorador: 404 si la captura automatica esta apagada."""
    @wraps(vista)
    def envuelta(request, *args, **kwargs):
        if not captura_habilitada():
            raise Http404('La captura automática no está disponible.')
        return vista(request, *args, **kwargs)
    return envuelta


def contexto_captura(request):
    """Context processor: expone captura_habilitada a las plantillas."""
    return {'captura_habilitada': captura_habilitada()}
