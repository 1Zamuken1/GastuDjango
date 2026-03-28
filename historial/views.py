from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .models import AccionHistorial

@login_required
def api_listar_historial(request):
    """
    Lista el historial de acciones del usuario para un módulo específico.
    Solo retorna los registros de los últimos 30 días.
    """
    modulo = request.GET.get('modulo', '').upper()
    
    if not modulo:
        return JsonResponse({'ok': False, 'error': 'Módulo requerido'}, status=400)
        
    fecha_limite = timezone.now() - timedelta(days=30)
    
    acciones = AccionHistorial.objects.filter(
        usuario=request.user,
        modulo=modulo,
        fecha_creacion__gte=fecha_limite,
        activo=True
    ).order_by('-fecha_creacion')
    
    resultados = []
    for accion in acciones:
        resultados.append({
            'id': accion.id,
            'accion': accion.accion,
            'descripcion': accion.descripcion,
            'referencia_id': accion.referencia_id,
            'monto_afectado': str(accion.monto_afectado) if accion.monto_afectado else None,
            'fecha': accion.fecha_creacion.strftime('%d %b %Y, %H:%M'),
            'fecha_iso': accion.fecha_creacion.isoformat(),
        })
        
    return JsonResponse({'ok': True, 'resultados': resultados})
