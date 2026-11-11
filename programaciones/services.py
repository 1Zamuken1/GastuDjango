from datetime import date, datetime
from decimal import Decimal

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

# Cuantas veces ocurre cada frecuencia en un mes promedio.
FACTOR_MENSUAL = {
    'DIARIO':     Decimal('30'),
    'SEMANAL':    Decimal('52') / Decimal('12'),
    'QUINCENAL':  Decimal('2'),
    'MENSUAL':    Decimal('1'),
    'BIMESTRAL':  Decimal('1') / Decimal('2'),
    'TRIMESTRAL': Decimal('1') / Decimal('3'),
    'SEMESTRAL':  Decimal('1') / Decimal('6'),
    'ANUAL':      Decimal('1') / Decimal('12'),
}


def monto_mensual_estimado(monto, frecuencia) -> Decimal:
    """Normaliza un monto recurrente a su equivalente mensual aproximado."""
    factor = FACTOR_MENSUAL.get(frecuencia)
    if factor is None or monto is None:
        return Decimal('0')
    return (Decimal(monto) * factor).quantize(Decimal('1'))


def ocurrencia(fecha_inicio: date, frecuencia: str, n: int) -> date:
    """Retorna la n-esima ocurrencia (0 = fecha_inicio).

    Se calcula siempre desde ``fecha_inicio`` para evitar el corrimiento
    que produce sumar meses en cadena (31 ene -> 28 feb -> 28 mar).
    """
    return fecha_inicio + DELTA_MAP[frecuencia] * n


def primera_ocurrencia_desde(fecha_inicio: date, frecuencia: str, desde: date) -> date | None:
    """Primera ocurrencia de la serie que cae en ``desde`` o despues."""
    if frecuencia not in DELTA_MAP:
        return None
    if fecha_inicio >= desde:
        return fecha_inicio
    n = 0
    fecha = fecha_inicio
    while fecha < desde:
        n += 1
        fecha = ocurrencia(fecha_inicio, frecuencia, n)
    return fecha


def ultima_ocurrencia_hasta(fecha_inicio: date, frecuencia: str, hasta: date) -> date | None:
    """Ultima ocurrencia de la serie que cae en ``hasta`` o antes (None si empieza despues)."""
    if frecuencia not in DELTA_MAP or fecha_inicio > hasta:
        return None
    n = 0
    while ocurrencia(fecha_inicio, frecuencia, n + 1) <= hasta:
        n += 1
    return ocurrencia(fecha_inicio, frecuencia, n)


def siguiente_ocurrencia(fecha_inicio: date, frecuencia: str, despues_de: date) -> date | None:
    """Primera ocurrencia estrictamente posterior a ``despues_de``."""
    if frecuencia not in DELTA_MAP:
        return None
    return primera_ocurrencia_desde(fecha_inicio, frecuencia, despues_de + relativedelta(days=1))


def proxima_inicial(fecha_inicio: date, frecuencia: str, hoy: date) -> date | None:
    """Proxima ejecucion de una programacion recien creada.

    Si empezo en el pasado solo queda pendiente el periodo en curso,
    no todos los periodos atrasados.
    """
    if fecha_inicio >= hoy:
        return fecha_inicio
    return ultima_ocurrencia_hasta(fecha_inicio, frecuencia, hoy)


def recalcular_tras_edicion(prog: Programacion, cambio_calendario: bool, reactivada: bool, hoy: date,
                            hoy_ya_resuelto: bool = False) -> None:
    """Ajusta ``proxima_ejecucion`` despues de editar o reactivar una programacion.

    - Si cambia la fecha de inicio o la frecuencia, la serie se recalcula
      desde la nueva fecha y se toma la primera ocurrencia desde hoy
      (desde mañana si la serie anterior ya resolvio el dia de hoy).
    - Si se reactiva una programacion pausada, los periodos que pasaron
      mientras estaba inactiva se omiten.
    """
    if cambio_calendario:
        desde = hoy + relativedelta(days=1) if hoy_ya_resuelto else hoy
        prog.proxima_ejecucion = primera_ocurrencia_desde(prog.fecha_inicio, prog.frecuencia, desde)
    elif reactivada and prog.proxima_ejecucion and prog.proxima_ejecucion < hoy:
        prog.proxima_ejecucion = primera_ocurrencia_desde(prog.fecha_inicio, prog.frecuencia, hoy)
    if prog.fecha_fin and prog.proxima_ejecucion and prog.proxima_ejecucion > prog.fecha_fin:
        prog.proxima_ejecucion = None


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
        'frecuencia_label': prog.get_frecuencia_display(),
        'tipo': prog.tipo,
        'categoria_id': prog.categoria_id,
        'categoria_nombre': prog.categoria.nombre,
        'categoria_icono': prog.categoria.icono,
        'fecha_inicio': prog.fecha_inicio.isoformat(),
        'fecha_pendiente': fecha_pendiente.isoformat(),
    }


def obtener_pendientes(usuario):
    """Recolecta todas las programaciones activas del usuario que están listas para ejecutar."""
    hoy = timezone.localdate()
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
    pendientes.sort(key=lambda p: p['fecha_pendiente'])
    return pendientes


def _fecha_registro_para(fecha_pendiente: date, hoy: date) -> datetime:
    """Fecha y hora con la que se registra el movimiento de una ejecucion.

    Usa el dia programado; si es hoy conserva la hora actual.
    """
    ahora = timezone.localtime()
    if fecha_pendiente == hoy:
        return ahora
    return timezone.make_aware(datetime.combine(fecha_pendiente, ahora.time().replace(microsecond=0)))


@transaction.atomic
def ejecutar_programacion(prog: Programacion, accion: str, request):
    """Ejecuta (acepta o rechaza) una programación. Crea Movimiento si acepta.

    El movimiento queda con la fecha programada, no con la fecha en que
    el usuario confirma, y el saldo se valida con el disponible real.
    """
    from dashboard.services import obtener_disponible

    hoy = timezone.localdate()
    fecha_pendiente = calcular_proxima_fecha(prog, hoy)
    if fecha_pendiente is None:
        return None, 'Esta programación no tiene ejecuciones pendientes.'

    if prog.frecuencia not in DELTA_MAP:
        return None, 'Frecuencia inválida.'

    proxima = siguiente_ocurrencia(prog.fecha_inicio, prog.frecuencia, fecha_pendiente)
    if prog.fecha_fin and proxima and proxima > prog.fecha_fin:
        proxima = None

    movimiento_data = None
    tipo = prog.categoria.tipo or prog.tipo

    if accion == 'aceptar':
        if tipo == Movimiento.TipoMovimiento.EGRESO:
            disponible = obtener_disponible(request.user, hoy.month, hoy.year)
            if disponible < prog.monto_programado:
                return None, 'El monto programado supera tu disponibilidad económica actual.'

        mov = Movimiento.objects.create(
            usuario=request.user,
            tipo=tipo,
            categoria=prog.categoria,
            monto=prog.monto_programado,
            descripcion=prog.descripcion or f'Programación automática: {prog.categoria.nombre}',
            fecha_registro=_fecha_registro_para(fecha_pendiente, hoy),
        )
        movimiento_data = {
            'id': mov.id,
            'tipo': mov.tipo,
            'monto': str(mov.monto),
            'categoria_nombre': prog.categoria.nombre,
            'descripcion': mov.descripcion,
            'fecha': fecha_pendiente.isoformat(),
        }
        from historial.models import AccionHistorial

        tipo_str = "ingreso" if tipo == "INGRESO" else "egreso"
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

    Programacion.objects.filter(pk=prog.pk).update(
        proxima_ejecucion=proxima,
        activo=proxima is not None,
        tipo=tipo,
    )
    prog.proxima_ejecucion = proxima
    prog.activo = proxima is not None

    return {
        'ok': True,
        'accion': accion,
        'proxima': proxima.isoformat() if proxima else None,
        'movimiento': movimiento_data,
    }, None
