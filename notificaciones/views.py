from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Notificacion


@login_required
def notificaciones_json(request):
    """
    Devuelve notificaciones del usuario en JSON.
    Acepta filtro opcional por modulo via GET ?modulo=EGRESOS.
    """
    modulo = request.GET.get('modulo', 'TODOS')
    queryset = Notificacion.objects.filter(usuario=request.user)

    # Filtrar por modulo solo si no es TODOS
    if modulo and modulo != 'TODOS':
        queryset = queryset.filter(modulo=modulo)

    queryset = queryset.order_by('-fecha_creacion')[:50]

    total_no_leidas = Notificacion.objects.filter(
        usuario=request.user, leida=False
    ).count()

    # Contar no leidas del modulo si hay filtro activo
    if modulo and modulo != 'TODOS':
        total_no_leidas_modulo = Notificacion.objects.filter(
            usuario=request.user, leida=False, modulo=modulo
        ).count()
    else:
        total_no_leidas_modulo = total_no_leidas

    return JsonResponse({
        'ok': True,
        'notificaciones': [
            dict_notif(n) for n in queryset
        ],
        'total_no_leidas': total_no_leidas,
        'total_no_leidas_modulo': total_no_leidas_modulo,
    })


def dict_notif(n):
    """Convierte una notificacion ORM a dict para JSON."""
    return {
        'id':          n.id,
        'tipo':        n.tipo,
        'modulo':      n.modulo,
        'titulo':      n.titulo,
        'descripcion': n.descripcion,
        'leida':       n.leida,
        'fecha':       n.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
    }


@require_POST
@login_required
def notificaciones_marcar_leidas(request):
    """
    Marca notificaciones como leidas.
    Sin body: marca TODAS como leidas.
    Con JSON body {ids: [1,2,3]}: marca solo esas.
    Con JSON body {modulo: 'INGRESOS'}: marca todas de ese modulo.
    """
    import json
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        body = {}

    ids = body.get('ids')
    modulo = body.get('modulo')

    qs = Notificacion.objects.filter(usuario=request.user, leida=False)

    if ids:
        qs = qs.filter(id__in=ids)
    elif modulo:
        qs = qs.filter(modulo=modulo)

    qs.update(leida=True)
    return JsonResponse({'ok': True, 'afectadas': qs.count()})
