from datetime import date
from dateutil.relativedelta import relativedelta
from dashboard.models import ResumenMensual
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from movimientos.models import Movimiento
from .models import Programacion, EjecucionProgramacion


# ── Mapa frecuencia → relativedelta ──────────────────────────────────────────

DELTA_MAP = {
    'DIARIO':     relativedelta(days=1),
    'SEMANAL':    relativedelta(weeks=1),
    'QUINCENAL':  relativedelta(days=15),
    'MENSUAL':    relativedelta(months=1),
    'BIMESTRAL':  relativedelta(months=2),
    'TRIMESTRAL': relativedelta(months=3),
    'SEMESTRAL':  relativedelta(months=6),
    'ANUAL':      relativedelta(years=1),
}


def calcular_proxima_fecha(programacion: Programacion, hoy: date) -> date | None:
    """
    Retorna la fecha pendiente si la programación debe ejecutarse HOY O ANTES.
    Usa proxima_ejecucion como punto de referencia principal.
    Solo retorna fecha si proxima_ejecucion <= hoy (es decir, ya tocó ejecutar).
    """
    if not programacion.activo:
        return None

    if programacion.fecha_fin and hoy > programacion.fecha_fin:
        return None

    delta = DELTA_MAP.get(programacion.frecuencia)
    if not delta:
        return None

    # Usar proxima_ejecucion si existe, sino fecha_inicio
    cursor = programacion.proxima_ejecucion or programacion.fecha_inicio

    # La ejecución es pendiente cuando cursor <= hoy (incluye hoy mismo)
    if cursor > hoy:
        return None

    return cursor


def desactivar_si_vencida(prog: Programacion, hoy: date) -> bool:
    """
    Desactiva la programación si su fecha_fin ya pasó, o si proxima_ejecucion
    supera fecha_fin (se agotó el rango). Retorna True si fue desactivada.
    """
    if not prog.activo:
        return False

    vencida = (
        (prog.fecha_fin and hoy > prog.fecha_fin)
        or (prog.fecha_fin and prog.proxima_ejecucion and prog.proxima_ejecucion > prog.fecha_fin)
    )

    if vencida:
        prog.activo = False
        prog.save(update_fields=['activo'])
        return True

    return False


def serializar_pendiente(prog: Programacion, fecha_pendiente: date) -> dict:
    return {
        'id':               prog.id,
        'descripcion':      prog.descripcion or '',
        'monto_programado': str(prog.monto_programado),
        'frecuencia':       prog.frecuencia,
        'tipo':             prog.tipo,
        'categoria_id':     prog.categoria_id,
        'categoria_nombre': prog.categoria.nombre,
        'fecha_inicio':     prog.fecha_inicio.isoformat(),
        'fecha_pendiente':  fecha_pendiente.isoformat(),
    }


# ── Endpoint 1: listar pendientes ─────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def programaciones_pendientes(request):

    hoy = timezone.now().date()

    programaciones = (
        Programacion.objects
        .filter(usuario=request.user, activo=True)
        .select_related('categoria')
    )

    pendientes = []

    for prog in programaciones:
        # Desactivar automáticamente si ya venció — sin importar si el usuario
        # procesó o no la última ejecución
        if desactivar_si_vencida(prog, hoy):
            continue

        fecha = calcular_proxima_fecha(prog, hoy)
        if fecha is not None:
            pendientes.append(serializar_pendiente(prog, fecha))

    return Response({'pendientes': pendientes})


# ── Endpoint 2: ejecutar (aceptar / rechazar) ─────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ejecutar_programacion(request, pk):

    try:
        prog = Programacion.objects.select_related('categoria').get(
            pk=pk, usuario=request.user, activo=True
        )
    except Programacion.DoesNotExist:
        return Response({'ok': False, 'error': 'Programación no encontrada.'}, status=404)

    accion = (request.data.get('accion') or '').lower()

    if accion not in ('aceptar', 'rechazar'):
        return Response(
            {'ok': False, 'error': 'accion debe ser "aceptar" o "rechazar".'},
            status=400
        )

    hoy = timezone.now().date()

    fecha_pendiente = calcular_proxima_fecha(prog, hoy)

    if fecha_pendiente is None:
        return Response(
            {'ok': False, 'error': 'Esta programación no tiene ejecuciones pendientes.'},
            status=400
        )

    delta = DELTA_MAP.get(prog.frecuencia)

    if not delta:
        return Response(
            {'ok': False, 'error': 'Frecuencia inválida.'},
            status=400
        )

    # La próxima ejecución avanza desde la fecha pendiente + delta
    proxima = fecha_pendiente + delta

    if prog.fecha_fin and proxima > prog.fecha_fin:
        proxima = None

    movimiento_data = None

    # ── ACEPTAR ─────────────────────────────────────────
    if accion == 'aceptar':

        resumen = ResumenMensual.objects.filter(usuario=request.user).first()

        if not resumen:
            return Response(
                {'ok': False, 'error': 'No existe resumen mensual para el usuario.'},
                status=400
            )

        if prog.tipo == Movimiento.TipoMovimiento.EGRESO:
            if resumen.disponible < prog.monto_programado:
                return Response(
                    {'ok': False, 'error': 'El monto programado supera la disponibilidad economica del usuario.'},
                    status=400
                )

        # Crear movimiento
        mov = Movimiento.objects.create(
            usuario=request.user,
            tipo=prog.tipo,
            categoria=prog.categoria,
            monto=prog.monto_programado,
            descripcion=prog.descripcion or f'Programación automática — {prog.categoria.nombre}',
        )

        movimiento_data = {
            'id':               mov.id,
            'tipo':             mov.tipo,
            'monto':            str(mov.monto),
            'categoria_nombre': mov.categoria.nombre,
            'descripcion':      mov.descripcion,
        }

        # Registrar ejecución
        EjecucionProgramacion.objects.create(
            programacion=prog,
            usuario=prog.usuario,
            fecha_ejecutada=fecha_pendiente,
            proxima_ejecucion=proxima,
            monto=prog.monto_programado,
            categoria_nombre=prog.categoria.nombre,
            tipo=prog.tipo,
            descripcion_snapshot=prog.descripcion,
            frecuencia_snapshot=prog.frecuencia,
        )

    # ── Avanzar programación (tanto aceptar como rechazar) ──────────
    prog.proxima_ejecucion = proxima
    prog.save(update_fields=['proxima_ejecucion'])

    
    if proxima is None:
        prog.activo = False
        prog.save(update_fields=['activo'])

    return Response({
        'ok':         True,
        'accion':     accion,
        'proxima':    proxima.isoformat() if proxima else None,
        'movimiento': movimiento_data,
    })


# ── Endpoint 3: historial ─────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def historial_ejecuciones(request):
    ejecuciones = EjecucionProgramacion.objects.filter(
        usuario=request.user
    ).order_by('-fecha_ejecutada')

    data = [{
        'descripcion':      e.descripcion_snapshot or '—',
        'categoria_nombre': e.categoria_nombre,
        'tipo':             e.tipo,
        'monto':            str(e.monto),
        'frecuencia':       e.frecuencia_snapshot or '—',
        'fecha_ejecutada':  str(e.fecha_ejecutada),
    } for e in ejecuciones]

    return Response({'ejecuciones': data})