"""
services.py — Logica de negocio de la app Ahorros.

Contiene las funciones de dominio para calcular cuotas, fechas,
recalcular aportes, gestionar estados de metas y armar el resumen
que muestran las cards y el detalle de cada meta.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from dateutil.relativedelta import relativedelta
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import AhorroMeta, AporteAhorro


# ── Calculo de periodos y fechas ────────────────────────────────────────────

# Limites de una meta: cada cuota es una fila en BD, asi que sin tope un solo
# POST podia generar millones de filas.
MAX_CUOTAS = 1000
MAX_ANIOS_META = 30

DELTA_FRECUENCIA = {
    'DIARIA': relativedelta(days=1),
    'SEMANAL': relativedelta(weeks=1),
    'QUINCENAL': relativedelta(days=15),
    'MENSUAL': relativedelta(months=1),
    'TRIMESTRAL': relativedelta(months=3),
    'SEMESTRAL': relativedelta(months=6),
    'ANUAL': relativedelta(years=1),
}


def hoy_local():
    """Fecha de hoy en la zona horaria del proyecto."""
    return timezone.localdate()


def calcular_periodo(frecuencia):
    """Retorna la cantidad aproximada de dias de una frecuencia (solo para ventanas)."""
    mapa = {
        'DIARIA': 1,
        'SEMANAL': 7,
        'QUINCENAL': 15,
        'MENSUAL': 30,
        'TRIMESTRAL': 90,
        'SEMESTRAL': 180,
        'ANUAL': 365,
    }
    return mapa.get(frecuencia, 30)


def delta_de(frecuencia):
    """relativedelta de una frecuencia; mensual por defecto."""
    return DELTA_FRECUENCIA.get(frecuencia, DELTA_FRECUENCIA['MENSUAL'])


def sumar_frecuencia(fecha, frecuencia):
    """Suma a una fecha un periodo de la frecuencia dada."""
    return fecha + delta_de(frecuencia)


def primera_cuota(fecha_base):
    """Fecha de la primera cuota: el dia siguiente a la creacion de la meta."""
    return fecha_base + timedelta(days=1)


def fecha_cuota(inicio, frecuencia, n):
    """Fecha de la cuota n (0 = primera), calculada siempre desde la primera.

    Sumar meses en cadena corre las fechas (31 ene -> 28 feb -> 28 mar);
    multiplicar el periodo desde el inicio las mantiene en el mismo dia.
    """
    return inicio + delta_de(frecuencia) * n


def calcular_campo_faltante(fecha_meta, cuotas, frecuencia, fecha_base=None):
    """
    Calcula el campo faltante (fecha_meta o cuotas) a partir del otro.

    La fecha meta es la fecha de la ultima cuota, de modo que siempre
    coincide con el calendario de cuotas.

    Returns:
        tuple: (fecha_meta, cuotas)
    """
    if not fecha_meta and not cuotas:
        raise ValueError("Debes enviar fecha_meta o cuotas")

    inicio = primera_cuota(fecha_base or hoy_local())

    if not cuotas:
        cuotas = 1
        # El tope evita que una fecha lejana con frecuencia diaria bloquee el servidor;
        # el formulario rechaza antes cualquier meta que supere MAX_CUOTAS.
        while cuotas <= MAX_CUOTAS and fecha_cuota(inicio, frecuencia, cuotas) <= fecha_meta:
            cuotas += 1
        return fecha_meta, cuotas

    return fecha_cuota(inicio, frecuencia, cuotas - 1), cuotas


# ── Generacion de cuotas ────────────────────────────────────────────────────

def generar_cuotas_preview(ahorro):
    """
    Genera una lista de objetos AporteAhorro sin guardar en BD.
    Se usa tanto para crear cuotas reales como para previsualizar
    la distribucion de montos.
    """
    if ahorro.cantidad_cuotas <= 0:
        raise ValueError("La cantidad de cuotas debe ser mayor a 0")

    inicio = primera_cuota(ahorro.fecha_creacion or hoy_local())
    monto_total = ahorro.monto_meta or Decimal('0.00')
    cantidad = ahorro.cantidad_cuotas

    monto_base = Decimal('0.00')
    resto = Decimal('0.00')
    if monto_total > 0:
        monto_base = (monto_total / cantidad).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        resto = monto_total - monto_base * cantidad

    return [
        AporteAhorro(
            ahorro=ahorro,
            estado_ap=AporteAhorro.EstadoAp.PENDIENTE.value,
            fecha_limite=fecha_cuota(inicio, ahorro.frecuencia, i),
            aporte_asignado=monto_base + resto if i == cantidad - 1 else monto_base,
        )
        for i in range(cantidad)
    ]


def generar_cuotas(ahorro):
    """Genera cuotas en BD para un ahorro dado."""
    cuotas = generar_cuotas_preview(ahorro)
    AporteAhorro.objects.bulk_create(cuotas)
    return cuotas


# ── Recalculo de aportes ────────────────────────────────────────────────────

def recalcular_aportes_restantes(ahorro):
    """
    Redistribuye el monto restante equitativamente entre las cuotas
    pendientes. Corrige la diferencia por redondeo en la ultima cuota.
    """
    aportes = list(AporteAhorro.objects.filter(ahorro=ahorro).order_by('fecha_limite'))
    aportado = sum(
        (a.aporte or Decimal('0.00'))
        for a in aportes
        if a.estado_ap == AporteAhorro.EstadoAp.APORTADO.value
    )
    restante = (ahorro.monto_meta or Decimal('0.00')) - aportado
    if restante <= Decimal('0.00'):
        return

    pendientes = [a for a in aportes if a.estado_ap == AporteAhorro.EstadoAp.PENDIENTE.value]
    if not pendientes:
        return

    asignado_base = (restante / len(pendientes)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    for p in pendientes:
        p.aporte_asignado = asignado_base
    diff = (restante - asignado_base * len(pendientes)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    pendientes[-1].aporte_asignado += diff
    AporteAhorro.objects.bulk_update(pendientes, ['aporte_asignado'])


def recalcular_aportes(ahorro):
    """
    Recalcula cuotas tras editar una meta: elimina pendientes/perdidas,
    genera cuotas nuevas y redistribuye montos.
    """
    todas = list(AporteAhorro.objects.filter(ahorro=ahorro).order_by('fecha_limite'))
    aportadas = [
        a for a in todas
        if a.estado_ap == AporteAhorro.EstadoAp.APORTADO.value and not a.es_extraordinario
    ]
    pendientes = [
        a for a in todas
        if a.estado_ap in (AporteAhorro.EstadoAp.PENDIENTE.value, AporteAhorro.EstadoAp.PERDIDO.value)
        and not a.es_extraordinario
    ]

    if pendientes:
        AporteAhorro.objects.filter(id__in=[p.id for p in pendientes]).delete()

    cuotas_nuevas = generar_cuotas_preview(ahorro)
    cuotas_aportadas_count = len(aportadas)

    if len(cuotas_nuevas) < cuotas_aportadas_count:
        ahorro.cantidad_cuotas = cuotas_aportadas_count
        ahorro.save(update_fields=['cantidad_cuotas'])
        cuotas_nuevas = generar_cuotas_preview(ahorro)

    cuotas_a_registrar = cuotas_nuevas[cuotas_aportadas_count:]

    if cuotas_a_registrar:
        AporteAhorro.objects.bulk_create(cuotas_a_registrar)
    else:
        total_aportado = sum(a.aporte for a in todas if a.estado_ap == AporteAhorro.EstadoAp.APORTADO.value and a.aporte)
        restante = (ahorro.monto_meta or Decimal('0.00')) - total_aportado

        if restante > Decimal('0.00'):
            ahorro.cantidad_cuotas = cuotas_aportadas_count + 1
            ahorro.save(update_fields=['cantidad_cuotas'])
            AporteAhorro.objects.create(
                ahorro=ahorro,
                estado_ap=AporteAhorro.EstadoAp.PENDIENTE.value,
                fecha_limite=sumar_frecuencia(hoy_local(), ahorro.frecuencia),
                aporte_asignado=Decimal('0.00'),
                es_extraordinario=False,
            )

    recalcular_aportes_restantes(ahorro)


def recalcular_fechas_cuotas(ahorro):
    """
    Reasigna las fechas limite de las cuotas no aportadas
    segun la nueva configuracion de la meta.
    """
    cuotas = list(
        AporteAhorro.objects.filter(ahorro=ahorro, es_extraordinario=False).order_by('fecha_limite')
    )
    nuevas = generar_cuotas_preview(ahorro)

    if len(nuevas) < len(cuotas):
        raise ValueError("No hay suficientes cuotas nuevas para reasignar fechas")

    for i, cuota in enumerate(cuotas):
        if cuota.estado_ap != AporteAhorro.EstadoAp.APORTADO.value:
            cuota.fecha_limite = nuevas[i].fecha_limite

    AporteAhorro.objects.bulk_update(cuotas, ['fecha_limite'])


# ── Gestion de estados ──────────────────────────────────────────────────────

def pasar_cuotas_a_perdidas(ahorro):
    """Marca como PERDIDO las cuotas pendientes cuya fecha limite ya paso."""
    return AporteAhorro.objects.filter(
        ahorro=ahorro,
        estado_ap=AporteAhorro.EstadoAp.PENDIENTE.value,
        fecha_limite__lt=hoy_local(),
        es_extraordinario=False,
    ).update(estado_ap=AporteAhorro.EstadoAp.PERDIDO.value)


def abandono_ahorro(ahorro):
    """
    Si las ultimas 3 cuotas vencidas son PERDIDO, marca la meta como ABANDONADO.
    Solo aplica si hay al menos 3 cuotas vencidas.
    """
    vencidas = list(
        AporteAhorro.objects.filter(
            ahorro=ahorro, es_extraordinario=False, fecha_limite__lt=hoy_local(),
        ).order_by('fecha_limite')
    )
    if len(vencidas) < 3:
        return False

    if all(a.estado_ap == AporteAhorro.EstadoAp.PERDIDO.value for a in vencidas[-3:]):
        if ahorro.estado not in (AhorroMeta.Estado.ABANDONADO.value, AhorroMeta.Estado.COMPLETADO.value):
            ahorro.estado = AhorroMeta.Estado.ABANDONADO.value
            ahorro.save(update_fields=['estado'])
            return True
    return False


def actualizar_estados_usuario(usuario):
    """Pone al dia las cuotas vencidas y el abandono de todas las metas abiertas.

    Antes esto solo pasaba al registrar un aporte, asi que una meta podia
    mostrar cuotas atrasadas como pendientes durante meses.
    """
    metas = AhorroMeta.objects.filter(
        usuario=usuario,
    ).exclude(estado=AhorroMeta.Estado.COMPLETADO.value)
    for meta in metas:
        if pasar_cuotas_a_perdidas(meta):
            abandono_ahorro(meta)


def cuota_disponible_pago(cuota, frecuencia, primera_pendiente=None):
    """
    Determina si una cuota pendiente esta dentro de la ventana
    de pago segun la frecuencia de la meta y es estrictamente
    la proxima a pagar (la primera pendiente).
    """
    if cuota is None or cuota.estado_ap != AporteAhorro.EstadoAp.PENDIENTE.value:
        return False

    if primera_pendiente is None:
        primera_pendiente = AporteAhorro.objects.filter(
            ahorro=cuota.ahorro,
            estado_ap=AporteAhorro.EstadoAp.PENDIENTE.value,
            es_extraordinario=False,
        ).order_by('fecha_limite').first()

    if not primera_pendiente or primera_pendiente.id != cuota.id:
        return False

    hoy = hoy_local()
    if cuota.fecha_limite < hoy:
        return False

    ventana = timedelta(days=3) if frecuencia == AhorroMeta.Frecuencia.DIARIA else delta_de(frecuencia)
    return cuota.fecha_limite <= hoy + ventana


def fecha_habilitacion(cuota, frecuencia):
    """Dia desde el que se puede pagar una cuota pendiente."""
    if frecuencia == AhorroMeta.Frecuencia.DIARIA:
        return cuota.fecha_limite - timedelta(days=3)
    return cuota.fecha_limite - delta_de(frecuencia)


def find_cuota_disponible(meta_id, usuario):
    """
    Encuentra la primera cuota PENDIENTE dentro de la ventana de pago
    para una meta dada.
    """
    meta = get_object_or_404(AhorroMeta, id=meta_id, usuario=usuario)
    primera = AporteAhorro.objects.filter(
        ahorro=meta, estado_ap=AporteAhorro.EstadoAp.PENDIENTE.value, es_extraordinario=False,
    ).order_by('fecha_limite').first()
    if primera and cuota_disponible_pago(primera, meta.frecuencia, primera_pendiente=primera):
        return primera
    return None


def obtener_aportes_por_meta(meta_id, usuario):
    """Retorna los aportes de una meta ordenados por fecha limite."""
    meta = get_object_or_404(AhorroMeta, id=meta_id, usuario=usuario)
    return AporteAhorro.objects.filter(ahorro=meta).order_by('-es_extraordinario', 'fecha_limite')


# ── Resumen para la interfaz ────────────────────────────────────────────────

ESTADOS_VISUALES = {
    'completada': 'Completada',
    'abandonada': 'Abandonada',
    'atrasada': 'Atrasada',
    'por_aportar': 'Por aportar',
    'al_dia': 'Al día',
    'sin_iniciar': 'Sin iniciar',
}


def proyectar_fin(meta, hoy=None):
    """Fecha en que se completaria la meta al ritmo de ahorro actual.

    El ritmo es lo acumulado dividido por los dias transcurridos desde la
    creacion. Retorna None si todavia no hay datos suficientes.
    """
    hoy = hoy or hoy_local()
    acumulado = meta.total_acumulado or Decimal('0')
    restante = (meta.monto_meta or Decimal('0')) - acumulado
    if acumulado <= 0 or restante <= 0:
        return None
    dias = (hoy - meta.fecha_creacion).days
    if dias < 7:
        return None
    ritmo_diario = acumulado / dias
    return hoy + timedelta(days=int((restante / ritmo_diario).to_integral_value(rounding=ROUND_HALF_UP)))


def resumen_meta(meta, cuotas=None, hoy=None):
    """Arma los datos que muestran la card y el detalle de una meta.

    Espera que las cuotas vencidas ya esten marcadas como PERDIDO
    (ver ``actualizar_estados_usuario``).
    """
    hoy = hoy or hoy_local()
    if cuotas is None:
        cuotas = list(meta.aporteahorro_set.all())
    regulares = sorted((c for c in cuotas if not c.es_extraordinario), key=lambda c: c.fecha_limite)

    pagadas = sum(1 for c in regulares if c.estado_ap == AporteAhorro.EstadoAp.APORTADO.value)
    perdidas = sum(1 for c in regulares if c.estado_ap == AporteAhorro.EstadoAp.PERDIDO.value)
    pendientes = [c for c in regulares if c.estado_ap == AporteAhorro.EstadoAp.PENDIENTE.value]
    proxima = pendientes[0] if pendientes else None
    disponible = cuota_disponible_pago(proxima, meta.frecuencia, primera_pendiente=proxima) if proxima else False

    monto_meta = meta.monto_meta or Decimal('0')
    acumulado = meta.total_acumulado or Decimal('0')
    porcentaje = int(min(100, (acumulado / monto_meta) * 100)) if monto_meta > 0 else 0

    if meta.estado == AhorroMeta.Estado.COMPLETADO.value:
        estado = 'completada'
    elif meta.estado == AhorroMeta.Estado.ABANDONADO.value:
        estado = 'abandonada'
    elif perdidas:
        estado = 'atrasada'
    elif disponible:
        estado = 'por_aportar'
    elif pagadas or acumulado > 0:
        estado = 'al_dia'
    else:
        estado = 'sin_iniciar'

    proyeccion = proyectar_fin(meta, hoy) if estado not in ('completada', 'abandonada') else None
    proyeccion_tarde = bool(proyeccion and meta.fecha_meta and proyeccion > meta.fecha_meta)

    return {
        'estado': estado,
        'estado_label': ESTADOS_VISUALES[estado],
        'porcentaje': porcentaje,
        'restante': max(monto_meta - acumulado, Decimal('0')),
        'pagadas': pagadas,
        'perdidas': perdidas,
        'pendientes': len(pendientes),
        'total_cuotas': len(regulares),
        'proxima': proxima,
        'proxima_disponible': disponible,
        'proxima_desde': fecha_habilitacion(proxima, meta.frecuencia) if proxima and not disponible else None,
        'dias_proxima': (proxima.fecha_limite - hoy).days if proxima else None,
        'proyeccion': proyeccion,
        'proyeccion_tarde': proyeccion_tarde,
    }
