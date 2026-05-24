"""
services.py — Logica de negocio de la app Ahorros.

Contiene las funciones de dominio para calcular cuotas, fechas,
recalcular aportes y gestionar estados de metas de ahorro.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.shortcuts import get_object_or_404
from .models import AhorroMeta, AporteAhorro


# ── Calculo de periodos y fechas ────────────────────────────────────────────

def calcular_periodo(frecuencia):
    """Retorna la cantidad de dias correspondiente a una frecuencia."""
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


def sumar_frecuencia(fecha, frecuencia):
    """Suma a una fecha la cantidad de dias de la frecuencia dada."""
    dias = calcular_periodo(frecuencia)
    return fecha + timedelta(days=dias)


def calcular_campo_faltante(fecha_meta, cuotas, frecuencia):
    """
    Calcula el campo faltante (fecha_meta o cuotas) a partir del otro.
    Requiere al menos uno de los dos valores.

    Returns:
        tuple: (fecha_meta, cuotas)
    """
    hoy = date.today()

    if not fecha_meta and not cuotas:
        raise ValueError("Debes enviar fecha_meta o cuotas")

    # Calcular cuotas a partir de fecha
    if not cuotas:
        dias = max(1, (fecha_meta - hoy).days)
        periodo = calcular_periodo(frecuencia)
        cuotas = max(1, dias // periodo)

    # Calcular fecha a partir de cuotas
    if not fecha_meta:
        fecha_calculada = hoy
        for _ in range(cuotas):
            fecha_calculada = sumar_frecuencia(fecha_calculada, frecuencia)
        return fecha_calculada, cuotas

    return fecha_meta, cuotas


# ── Generacion de cuotas ────────────────────────────────────────────────────

def generar_cuotas_preview(ahorro):
    """
    Genera una lista de objetos AporteAhorro sin guardar en BD.
    Se usa tanto para crear cuotas reales como para previsualizar
    la distribucion de montos.
    """
    if ahorro.cantidad_cuotas <= 0:
        raise ValueError("La cantidad de cuotas debe ser mayor a 0")

    cuotas = []
    fecha = ahorro.fecha_creacion + timedelta(days=1)

    monto_total = ahorro.monto_meta or Decimal('0.00')
    cantidad = ahorro.cantidad_cuotas

    monto_base = Decimal('0.00')
    resto = Decimal('0.00')

    if monto_total > 0:
        monto_base = (monto_total / cantidad).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        total_calculado = monto_base * cantidad
        resto = monto_total - total_calculado

    for i in range(cantidad):
        if i > 0:
            fecha = sumar_frecuencia(fecha, ahorro.frecuencia)

        cuota = AporteAhorro(
            ahorro=ahorro,
            estado_ap=AporteAhorro.EstadoAp.PENDIENTE,
            fecha_limite=fecha,
            aporte_asignado=(
                monto_base + resto if i == cantidad - 1 else monto_base
            ),
        )
        cuotas.append(cuota)

    return cuotas


def generar_cuotas(ahorro):
    """Genera cuotas en BD para un ahorro dado."""
    cuotas = generar_cuotas_preview(ahorro)
    for c in cuotas:
        c.ahorro = ahorro
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
        (a.aporte if a.aporte else Decimal('0.00'))
        for a in aportes
        if a.estado_ap == AporteAhorro.EstadoAp.APORTADO
    )
    monto_meta = ahorro.monto_meta or Decimal('0.00')
    restante = monto_meta - aportado

    if restante <= Decimal('0.00'):
        return

    pendientes = [
        a for a in aportes
        if a.estado_ap == AporteAhorro.EstadoAp.PENDIENTE
    ]
    cuotas_faltantes = len(pendientes)

    if cuotas_faltantes == 0:
        return

    asignado_base = (restante / cuotas_faltantes).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    for p in pendientes:
        p.aporte_asignado = asignado_base

    AporteAhorro.objects.bulk_update(pendientes, ['aporte_asignado'])

    # Corregir diferencia por redondeo
    suma_asignados = sum(
        (p.aporte_asignado or Decimal('0.00'))
        for p in pendientes
    )
    diff = (restante - suma_asignados).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    if diff != Decimal('0.00') and pendientes:
        ultima = pendientes[-1]
        ultima.aporte_asignado = (ultima.aporte_asignado or Decimal('0.00')) + diff
        ultima.save()


def recalcular_aportes(ahorro):
    """
    Recalcula cuotas tras editar una meta: elimina pendientes/perdidas,
    genera cuotas nuevas y redistribuye montos.
    """
    todas = list(AporteAhorro.objects.filter(ahorro=ahorro).order_by('fecha_limite'))
    aportadas = [
        a for a in todas
        if a.estado_ap == AporteAhorro.EstadoAp.APORTADO
    ]
    pendientes = [
        a for a in todas
        if a.estado_ap in [
            AporteAhorro.EstadoAp.PENDIENTE,
            AporteAhorro.EstadoAp.PERDIDO,
        ]
    ]

    if pendientes:
        AporteAhorro.objects.filter(id__in=[p.id for p in pendientes]).delete()

    cuotas_nuevas = generar_cuotas_preview(ahorro)
    cuotas_aportadas_count = len(aportadas)

    if len(cuotas_nuevas) < cuotas_aportadas_count:
        raise ValueError(
            "No se puede reducir cuotas por debajo de las ya aportadas"
        )

    cuotas_a_registrar = cuotas_nuevas[cuotas_aportadas_count:]
    for c in cuotas_a_registrar:
        c.ahorro = ahorro

    if cuotas_a_registrar:
        AporteAhorro.objects.bulk_create(cuotas_a_registrar)

    recalcular_aportes_restantes(ahorro)


def recalcular_fechas_cuotas(ahorro):
    """
    Reasigna las fechas limite de las cuotas no aportadas
    segun la nueva configuracion de la meta.
    """
    cuotas = list(
        AporteAhorro.objects
        .filter(ahorro=ahorro)
        .order_by('fecha_limite')
    )
    nuevas = generar_cuotas_preview(ahorro)

    if len(nuevas) < len(cuotas):
        raise ValueError("No hay suficientes cuotas nuevas para reasignar fechas")

    for i, cuota in enumerate(cuotas):
        if cuota.estado_ap == AporteAhorro.EstadoAp.APORTADO:
            continue
        cuota.fecha_limite = nuevas[i].fecha_limite

    AporteAhorro.objects.bulk_update(cuotas, ['fecha_limite'])


# ── Gestion de estados ──────────────────────────────────────────────────────

def pasar_cuotas_a_perdidas(ahorro):
    """Marca como PERDIDO las cuotas pendientes cuya fecha limite ya paso."""
    hoy = date.today()
    AporteAhorro.objects.filter(
        ahorro=ahorro,
        estado_ap=AporteAhorro.EstadoAp.PENDIENTE,
        fecha_limite__lt=hoy,
    ).update(estado_ap=AporteAhorro.EstadoAp.PERDIDO)


def abandono_ahorro(ahorro):
    """
    Si las ultimas 3 cuotas son PERDIDO, marca la meta como ABANDONADO.
    Solo aplica si hay al menos 3 cuotas.
    """
    todas = list(AporteAhorro.objects.filter(ahorro=ahorro).order_by('fecha_limite'))

    if len(todas) < 3:
        return

    ultimas_3 = todas[-3:]
    if all(a.estado_ap == AporteAhorro.EstadoAp.PERDIDO for a in ultimas_3):
        if ahorro.estado != AhorroMeta.Estado.ABANDONADO:
            ahorro.estado = AhorroMeta.Estado.ABANDONADO
            ahorro.save()


def cuota_disponible_pago(cuota, frecuencia):
    """
    Determina si una cuota pendiente esta dentro de la ventana
    de pago segun la frecuencia de la meta y es estrictamente
    la proxima a pagar (la primera pendiente).
    """
    from dateutil.relativedelta import relativedelta

    if cuota is None or cuota.estado_ap != AporteAhorro.EstadoAp.PENDIENTE:
        return False
        
    # Verificar que esta cuota sea la primera PENDIENTE de la meta
    primera_pendiente = AporteAhorro.objects.filter(
        ahorro=cuota.ahorro,
        estado_ap=AporteAhorro.EstadoAp.PENDIENTE
    ).order_by('fecha_limite').first()

    if not primera_pendiente or primera_pendiente.id != cuota.id:
        return False

    hoy = date.today()
    limite = cuota.fecha_limite

    ventanas = {
        AhorroMeta.Frecuencia.DIARIA: timedelta(days=3),
        AhorroMeta.Frecuencia.SEMANAL: timedelta(days=7),
        AhorroMeta.Frecuencia.QUINCENAL: timedelta(days=15),
        AhorroMeta.Frecuencia.MENSUAL: relativedelta(months=1),
        AhorroMeta.Frecuencia.TRIMESTRAL: relativedelta(months=3),
        AhorroMeta.Frecuencia.SEMESTRAL: relativedelta(months=6),
        AhorroMeta.Frecuencia.ANUAL: relativedelta(years=1),
    }

    ventana = ventanas.get(frecuencia, timedelta(days=3))
    return limite <= hoy + ventana


def find_cuota_disponible(meta_id, usuario):
    """
    Encuentra la primera cuota PENDIENTE dentro de la ventana de pago
    para una meta dada.
    """
    meta = get_object_or_404(AhorroMeta, id=meta_id, usuario=usuario)
    cuotas = AporteAhorro.objects.filter(ahorro=meta).order_by('fecha_limite')

    for c in cuotas:
        if c.estado_ap == AporteAhorro.EstadoAp.PENDIENTE:
            if cuota_disponible_pago(c, meta.frecuencia):
                return c
    return None


def obtener_aportes_por_meta(meta_id, usuario):
    """Retorna los aportes de una meta ordenados por fecha limite."""
    meta = get_object_or_404(AhorroMeta, id=meta_id, usuario=usuario)
    return AporteAhorro.objects.filter(ahorro=meta).order_by('fecha_limite')
