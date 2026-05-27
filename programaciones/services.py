from datetime import date

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone

from movimientos.models import Movimiento
from .models import Programacion

# Mapeo de frecuencia legible a delta temporal computable.
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
    """Retorna la fecha pendiente de una programación, o None si no hay nada que ejecutar."""
    if not programacion.activo:
        return None
    if programacion.fecha_fin and hoy > programacion.fecha_fin:
        return None
    delta = DELTA_MAP.get(programacion.frecuencia)
    if not delta:
        return None
    cursor = programacion.proxima_ejecucion or programacion.fecha_inicio
    if cursor > hoy:
        return None
    return cursor


def desactivar_si_vencida(prog: Programacion, hoy: date) -> bool:
    """Desactiva la programación si su fecha_fin ya pasó. Retorna True si se desactivó."""
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
    """Convierte una programación + fecha pendiente en el dict que consume el frontend."""
    return {
        'id': prog.id,
        'descripcion': prog.descripcion or '',
        'monto_programado': str(prog.monto_programado),
        'frecuencia': prog.frecuencia,
        'tipo': prog.tipo,
        'categoria_id': prog.categoria_id,
        'categoria_nombre': prog.categoria.nombre,
        'fecha_inicio': prog.fecha_inicio.isoformat(),
        'fecha_pendiente': fecha_pendiente.isoformat(),
    }


def obtener_pendientes(usuario):
    """Recolecta todas las programaciones activas del usuario que están listas para ejecutar."""
    hoy = timezone.now().date()
    programaciones = Programacion.objects.filter(
        usuario=usuario, activo=True
    ).select_related('categoria')

    pendientes = []
    for prog in programaciones:
        if desactivar_si_vencida(prog, hoy):
            continue
        fecha = calcular_proxima_fecha(prog, hoy)
        if fecha is not None:
            pendientes.append(serializar_pendiente(prog, fecha))
    return pendientes


@transaction.atomic
def ejecutar_programacion(prog: Programacion, accion: str, request):
    """Ejecuta (acepta o rechaza) una programación. Crea Movimiento si acepta."""
    from dashboard.models import ResumenMensual

    hoy = timezone.now().date()
    fecha_pendiente = calcular_proxima_fecha(prog, hoy)
    if fecha_pendiente is None:
        return None, 'Esta programación no tiene ejecuciones pendientes.'

    delta = DELTA_MAP.get(prog.frecuencia)
    if not delta:
        return None, 'Frecuencia inválida.'

    proxima = fecha_pendiente + delta
    if prog.fecha_fin and proxima > prog.fecha_fin:
        proxima = None

    movimiento_data = None

    if accion == 'aceptar':
        resumen = ResumenMensual.objects.filter(usuario=request.user).first()
        if not resumen:
            return None, 'No existe resumen mensual para el usuario.'
        if prog.tipo == Movimiento.TipoMovimiento.EGRESO and resumen.disponible < prog.monto_programado:
            return None, 'El monto programado supera la disponibilidad economica del usuario.'

        mov = Movimiento.objects.create(
            usuario=request.user,
            tipo=prog.tipo,
            categoria=prog.categoria,
            monto=prog.monto_programado,
            descripcion=prog.descripcion or f'Programación automática — {prog.categoria.nombre}',
        )
        movimiento_data = {
            'id': mov.id,
            'tipo': mov.tipo,
            'monto': str(mov.monto),
            'categoria_nombre': prog.categoria.nombre,
            'descripcion': mov.descripcion,
        }
        from historial.models import AccionHistorial

        tipo_str = "ingreso" if prog.tipo == "INGRESO" else "egreso"
        modulo_mov = (
            AccionHistorial.ModuloChoices.INGRESOS
            if prog.tipo == "INGRESO"
            else AccionHistorial.ModuloChoices.EGRESOS
        )
        desc_mov = f"Se registró un {tipo_str} automático en '{prog.categoria.nombre}'"
        if prog.descripcion:
            desc_mov += f" ({prog.descripcion})"

        AccionHistorial.objects.create(
            usuario=prog.usuario,
            accion=AccionHistorial.AccionChoices.CREACION,
            modulo=modulo_mov,
            descripcion=desc_mov,
            referencia_id=str(mov.id),
            monto_afectado=prog.monto_programado,
        )

        desc_prog = f"Se ejecutó una programación de {tipo_str} en '{prog.categoria.nombre}'"
        if prog.descripcion:
            desc_prog += f" ({prog.descripcion})"

        AccionHistorial.objects.create(
            usuario=prog.usuario,
            accion=AccionHistorial.AccionChoices.CREACION,
            modulo=AccionHistorial.ModuloChoices.PROGRAMACIONES,
            descripcion=desc_prog,
            referencia_id=str(prog.id),
            monto_afectado=prog.monto_programado,
        )

    prog.proxima_ejecucion = proxima
    prog.activo = proxima is not None
    prog.save(update_fields=['proxima_ejecucion', 'activo'])

    return {
        'ok': True,
        'accion': accion,
        'proxima': proxima.isoformat() if proxima else None,
        'movimiento': movimiento_data,
    }, None

