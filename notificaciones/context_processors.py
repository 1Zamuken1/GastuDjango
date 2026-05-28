from notificaciones.models import Notificacion

def notificaciones_count(request):
    """
    Agrega el contador global de notificaciones no leídas a todas las vistas.
    Resuelve el bug donde el badge desaparecía en vistas fuera de dashboard.
    """
    if request.user.is_authenticated:
        total = Notificacion.objects.filter(usuario=request.user, leida=False).count()
        return {'global_notificaciones_count': total}
    return {}
