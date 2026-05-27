"""Vistas de lógica adicional: pendientes, ejecución e historial.

Separa los endpoints que no son CRUD puro del ViewSet principal.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Programacion
from .services import obtener_pendientes, ejecutar_programacion


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def programaciones_pendientes(request):
    """Lista las programaciones del usuario que están listas para ejecutarse hoy."""
    pendientes = obtener_pendientes(request.user)
    return Response({'pendientes': pendientes})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ejecutar_programacion_view(request, pk):
    """Acepta o rechaza una programación pendiente identificada por su pk."""
    accion = (request.data.get('accion') or '').lower()
    if accion not in ('aceptar', 'rechazar'):
        return Response(
            {'ok': False, 'error': 'accion debe ser "aceptar" o "rechazar".'},
            status=400,
        )

    try:
        prog = Programacion.objects.select_related('categoria').get(
            pk=pk, usuario=request.user, activo=True
        )
    except Programacion.DoesNotExist:
        return Response(
            {'ok': False, 'error': 'Programación no encontrada.'}, status=404
        )

    resultado, error = ejecutar_programacion(prog, accion, request)
    if error:
        return Response({'ok': False, 'error': error}, status=400)

    return Response(resultado)

