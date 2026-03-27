from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notificacion


@login_required
def notificaciones_json(request):
    """
    Devuelve las últimas 15 notificaciones del usuario en formato JSON.
    Usado por el panel de notificaciones del topbar.
    """
    notifs = (
        Notificacion.objects
        .filter(usuario=request.user)
        .order_by('-fecha_creacion')[:15]
    )
    return JsonResponse({
        'ok': True,
        'notificaciones': [
            {
                'id':          n.id,
                'tipo':        n.tipo,
                'titulo':      n.titulo,
                'descripcion': n.descripcion,
                'leida':       n.leida,
                'fecha':       n.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
            }
            for n in notifs
        ]
    })