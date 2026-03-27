"""
Servicio de análisis de alertas financieras.

Equivalente al AlertAnalysisService.java original, adaptado a Django/Python.
Sin preferencias de usuario: todas las alertas están siempre activas con
umbrales fijos razonables definidos como constantes al inicio del archivo.
"""

from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db.models import Sum, Count, Q


# ─── Umbrales fijos (reemplazan las PreferenciasUsuario) ──────────────────────

# Tendencias
UMBRAL_GASTO_INCREMENTAL_PCT   = Decimal('20')   # % sobre promedio histórico
UMBRAL_GASTO_INCREMENTAL_MESES = 3               # meses de historial a comparar
UMBRAL_REDUCCION_INGRESOS_PCT  = Decimal('20')   # % de caída respecto al promedio

# Conceptos
UMBRAL_CONCENTRACION_PCT       = Decimal('50')   # % del total de egresos en 1 concepto
UMBRAL_CONCEPTO_SIN_USO_DIAS   = 30              # días sin registros para concepto recurrente

# Tiempo
UMBRAL_VELOCIDAD_GASTO_PCT     = Decimal('70')   # % gastado antes del día 15
UMBRAL_VELOCIDAD_GASTO_DIA     = 15              # día límite para disparar la alerta
UMBRAL_INACTIVIDAD_INGRESOS    = 15              # días sin ingresos
UMBRAL_EGRESOS_AGRUPADOS_N     = 5               # cantidad de egresos en la ventana
UMBRAL_EGRESOS_AGRUPADOS_HORAS = 2               # horas que define la ventana

# Micro-gastos
UMBRAL_MICRO_MONTO_MAX         = Decimal('10000')  # monto máximo para considerarse micro-gasto
UMBRAL_MICRO_CANTIDAD          = 10               # cantidad de micro-gastos para disparar alerta
UMBRAL_HORMIGA_MONTO_DIA       = Decimal('50000') # total diario de gastos hormiga
UMBRAL_HORMIGA_TRANSACCIONES   = 3               # mínimo de transacciones para calificar

# Predictivas
UMBRAL_COMPARACION_PERIODO_PCT = Decimal('20')   # % de cambio vs mes anterior
UMBRAL_DIA_MES_CRITICO_PCT     = Decimal('80')   # % gastado del ingreso para alerta crítica

# Inconsistencias
UMBRAL_EGRESOS_SIN_CONCEPTO    = 5               # cantidad mínima para alertar
UMBRAL_INGRESO_INUSUAL_MULT    = Decimal('2.5')  # multiplicador sobre el promedio mensual


# ─── Utilidad: anti-duplicado ─────────────────────────────────────────────────

def _crear_notificacion(usuario, tipo, titulo, descripcion):
    """
    Crea una notificación para el usuario solo si no existe
    una igual (mismo tipo, no leída) registrada hoy.
    Evita saturar al usuario con la misma alerta varias veces al día.
    """
    from .models import Notificacion

    hoy = timezone.now().date()
    ya_existe = Notificacion.objects.filter(
        usuario=usuario,
        tipo=tipo,
        leida=False,
        fecha_creacion__date=hoy,
    ).exists()

    if not ya_existe:
        Notificacion.objects.create(
            usuario=usuario,
            tipo=tipo,
            titulo=titulo,
            descripcion=descripcion,
        )


# ─── Punto de entrada principal ───────────────────────────────────────────────

def analizar_movimiento(usuario, movimiento):
    """
    Analiza un movimiento recién creado o editado y genera las
    notificaciones que correspondan según su tipo.

    Args:
        usuario:     instancia del usuario dueño del movimiento.
        movimiento:  instancia del Movimiento recién guardado.
    """
    if movimiento.tipo == 'EGRESO':
        _analizar_egreso(usuario, movimiento)
    else:
        _analizar_ingreso(usuario, movimiento)


# ─── Análisis por tipo ────────────────────────────────────────────────────────

def _analizar_egreso(usuario, egreso):
    _check_umbral_mensual(usuario, egreso)
    _check_deficit(usuario, egreso)
    _check_egreso_grande(usuario, egreso)
    _check_gasto_incremental(usuario, egreso)
    _check_patron_inusual_egresos(usuario, egreso)
    _check_concentracion_gastos(usuario, egreso)
    _check_velocidad_gasto(usuario, egreso)
    _check_egresos_agrupados(usuario, egreso)
    _check_balance_critico(usuario, egreso)
    _check_micro_gastos(usuario, egreso)
    _check_gastos_hormiga(usuario, egreso)
    _check_proyeccion_sobregasto(usuario, egreso)
    _check_comparacion_periodo_egresos(usuario, egreso)
    _check_dia_mes_critico(usuario, egreso)
    _check_egreso_sin_concepto(usuario, egreso)


def _analizar_ingreso(usuario, ingreso):
    _check_reduccion_ingresos(usuario, ingreso)
    _check_inactividad_ingresos(usuario, ingreso)
    _check_ingreso_inusual(usuario, ingreso)
    _check_concepto_sin_uso(usuario, ingreso)


# ─── Helpers de consulta ─────────────────────────────────────────────────────

def _total_en_rango(usuario, tipo, inicio, fin):
    """Suma de montos de movimientos del usuario en un rango de fechas."""
    from movimientos.models import Movimiento  # ajusta el import a tu app real

    resultado = Movimiento.objects.filter(
        usuario=usuario,
        tipo=tipo,
        fecha_registro__range=(inicio, fin),
    ).aggregate(total=Sum('monto'))['total']
    return resultado or Decimal('0')


def _count_en_rango(usuario, tipo, inicio, fin):
    """Cantidad de movimientos del usuario en un rango de fechas."""
    from movimientos.models import Movimiento

    return Movimiento.objects.filter(
        usuario=usuario,
        tipo=tipo,
        fecha_registro__range=(inicio, fin),
    ).count()


def _inicio_mes(dt=None):
    """Retorna el primer instante del mes del datetime dado (o del actual)."""
    dt = dt or timezone.now()
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _fin_mes(dt):
    """Retorna el último instante del mes del datetime dado."""
    import calendar
    ultimo_dia = calendar.monthrange(dt.year, dt.month)[1]
    return dt.replace(day=ultimo_dia, hour=23, minute=59, second=59, microsecond=999999)


# ─── Alertas originales (ya existían en services.py) ─────────────────────────

def _check_umbral_mensual(usuario, egreso):
    """Alerta cuando los egresos del mes superan el umbral configurado."""
    try:
        from dashboard.models import ResumenMensual
        from .models import Notificacion

        now = timezone.now()
        resumen = ResumenMensual.objects.filter(
            usuario=usuario, mes=now.month, anio=now.year
        ).first()
        if not resumen or resumen.total_ingresos <= 0:
            return

        try:
            umbral = usuario.preferencias.umbral_advertencia_porcentaje
        except Exception:
            umbral = Decimal('80')

        porcentaje = (resumen.total_egresos / resumen.total_ingresos * 100).quantize(
            Decimal('0.1'), rounding=ROUND_HALF_UP
        )
        if porcentaje >= umbral:
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.UMBRAL_MENSUAL,
                titulo='Umbral de gastos alcanzado',
                descripcion=(
                    f'Has gastado el {porcentaje}% de tus ingresos '
                    f'de este mes (${resumen.total_egresos:,.2f} de '
                    f'${resumen.total_ingresos:,.2f}).'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_umbral_mensual: {e}')


def _check_deficit(usuario, egreso):
    """Alerta cuando los egresos superan los ingresos del mes."""
    try:
        from dashboard.models import ResumenMensual
        from .models import Notificacion

        now = timezone.now()
        resumen = ResumenMensual.objects.filter(
            usuario=usuario, mes=now.month, anio=now.year
        ).first()
        if resumen and resumen.deficit:
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.DEFICIT,
                titulo='Balance en déficit',
                descripcion=(
                    f'Tus egresos (${resumen.total_egresos:,.2f}) superan '
                    f'tus ingresos (${resumen.total_ingresos:,.2f}) este mes.'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_deficit: {e}')


def _check_egreso_grande(usuario, egreso):
    """Alerta cuando un egreso individual supera el % configurado del ingreso mensual."""
    try:
        from dashboard.models import ResumenMensual
        from .models import Notificacion

        now = timezone.now()
        resumen = ResumenMensual.objects.filter(
            usuario=usuario, mes=now.month, anio=now.year
        ).first()
        if not resumen or resumen.total_ingresos <= 0:
            return

        try:
            umbral_pct = usuario.preferencias.egreso_grande_porcentaje
        except Exception:
            umbral_pct = Decimal('30')

        porcentaje = (egreso.monto / resumen.total_ingresos * 100).quantize(
            Decimal('0.1'), rounding=ROUND_HALF_UP
        )
        if porcentaje >= umbral_pct:
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.EGRESO_GRANDE,
                titulo='Egreso grande registrado',
                descripcion=(
                    f'Registraste un egreso de ${egreso.monto:,.2f} que representa '
                    f'el {porcentaje}% de tus ingresos del mes.'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_egreso_grande: {e}')


# ─── Alertas de tendencias ────────────────────────────────────────────────────

def _check_gasto_incremental(usuario, egreso):
    """
    Alerta cuando los egresos del mes actual superan el promedio histórico
    de los últimos N meses en más del umbral configurado.
    """
    try:
        from .models import Notificacion

        now     = timezone.now()
        inicio  = _inicio_mes(now)
        total_actual = _total_en_rango(usuario, 'EGRESO', inicio, now)

        suma_historica = Decimal('0')
        meses = UMBRAL_GASTO_INCREMENTAL_MESES
        for i in range(1, meses + 1):
            # retroceder i meses
            mes_dt  = (now.replace(day=1) - timezone.timedelta(days=1)).replace(day=1)
            for _ in range(i - 1):
                mes_dt = (mes_dt.replace(day=1) - timezone.timedelta(days=1)).replace(day=1)
            inicio_h = _inicio_mes(mes_dt)
            fin_h    = _fin_mes(mes_dt)
            suma_historica += _total_en_rango(usuario, 'EGRESO', inicio_h, fin_h)

        if suma_historica <= 0:
            return

        promedio = (suma_historica / meses).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if promedio <= 0:
            return

        incremento = ((total_actual - promedio) / promedio * 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        if incremento >= UMBRAL_GASTO_INCREMENTAL_PCT:
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.GASTO_INCREMENTAL,
                titulo='Gasto incremental detectado',
                descripcion=(
                    f'Tus egresos este mes (${total_actual:,.2f}) superan el promedio '
                    f'de los últimos {meses} meses (${promedio:,.2f}) en un {incremento}%. '
                    f'Considera revisar tus gastos.'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_gasto_incremental: {e}')


def _check_reduccion_ingresos(usuario, ingreso):
    """
    Alerta cuando los ingresos del mes actual están por debajo
    del promedio de los últimos 3 meses en más del umbral configurado.
    """
    try:
        from .models import Notificacion

        now    = timezone.now()
        inicio = _inicio_mes(now)
        total_actual = _total_en_rango(usuario, 'INGRESO', inicio, now)

        suma_historica = Decimal('0')
        for i in range(1, 4):
            mes_dt = now.replace(day=1)
            for _ in range(i):
                mes_dt = (mes_dt - timezone.timedelta(days=1)).replace(day=1)
            inicio_h = _inicio_mes(mes_dt)
            fin_h    = _fin_mes(mes_dt)
            suma_historica += _total_en_rango(usuario, 'INGRESO', inicio_h, fin_h)

        if suma_historica <= 0:
            return

        promedio = (suma_historica / 3).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        reduccion = ((promedio - total_actual) / promedio * 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        if reduccion >= UMBRAL_REDUCCION_INGRESOS_PCT:
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.REDUCCION_INGRESOS,
                titulo='Reducción de ingresos detectada',
                descripcion=(
                    f'Tus ingresos este mes (${total_actual:,.2f}) son un {reduccion}% '
                    f'menores al promedio de los últimos 3 meses (${promedio:,.2f}).'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_reduccion_ingresos: {e}')


def _check_patron_inusual_egresos(usuario, egreso):
    """
    Alerta cuando hoy hay más del doble del promedio diario de egresos
    y la cantidad supera un mínimo absoluto.
    """
    try:
        from .models import Notificacion

        now       = timezone.now()
        inicio_hoy = now.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_hoy    = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        transacciones_hoy = _count_en_rango(usuario, 'EGRESO', inicio_hoy, fin_hoy)
        inicio_mes        = _inicio_mes(now)
        dias_del_mes      = (now.date() - inicio_mes.date()).days + 1
        transacciones_mes = _count_en_rango(usuario, 'EGRESO', inicio_mes, fin_hoy)

        if dias_del_mes <= 0:
            return

        promedio_diario = transacciones_mes / dias_del_mes
        if transacciones_hoy > promedio_diario * 2 and transacciones_hoy >= 8:
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.PATRON_INUSUAL,
                titulo='Patrón inusual de gastos',
                descripcion=(
                    f'Hoy has registrado {transacciones_hoy} egresos, significativamente '
                    f'más que tu promedio diario ({promedio_diario:.1f}). '
                    f'Verifica que no haya errores.'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_patron_inusual_egresos: {e}')


# ─── Alertas de conceptos ─────────────────────────────────────────────────────

def _check_concentracion_gastos(usuario, egreso):
    """
    Alerta cuando un solo concepto concentra más del umbral configurado
    del total de egresos del mes.
    """
    try:
        from movimientos.models import Movimiento
        from .models import Notificacion

        now    = timezone.now()
        inicio = _inicio_mes(now)

        total_egresos = _total_en_rango(usuario, 'EGRESO', inicio, now)
        if total_egresos <= 0:
            return

        # Agrupar egresos del mes por concepto
        stats = (
            Movimiento.objects.filter(
                usuario=usuario,
                tipo='EGRESO',
                fecha_registro__range=(inicio, now),
            )
            .values('categoria', 'categoria__nombre')
            .annotate(total=Sum('monto'))
        )

        for stat in stats:
            total_concepto = stat['total'] or Decimal('0')
            porcentaje = (total_concepto / total_egresos * 100).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            if porcentaje >= UMBRAL_CONCENTRACION_PCT:
             _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.CONCENTRACION_GASTO,
                titulo='Concentración de gastos en una categoría',
                descripcion=(
                    f"La categoría '{stat['categoria__nombre']}' representa el {porcentaje}% "
                    f"de tus egresos este mes (${total_concepto:,.2f} de ${total_egresos:,.2f}). "
                    f"Considera diversificar."
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_concentracion_gastos: {e}')


def _check_concepto_sin_uso(usuario, ingreso):
    """
    Alerta cuando una categoría que apareció en 3+ de los últimos 6 meses
    no tiene registros recientes (más de N días de inactividad).
    """
    try:
        from movimientos.models import Movimiento
        from .models import Notificacion

        now = timezone.now()
        apariciones = {}

        for i in range(1, 7):
            mes_dt = now.replace(day=1)
            for _ in range(i):
                mes_dt = (mes_dt - timezone.timedelta(days=1)).replace(day=1)
            inicio_h = _inicio_mes(mes_dt)
            fin_h    = _fin_mes(mes_dt)

            categorias_mes = (
                Movimiento.objects.filter(
                    usuario=usuario,
                    tipo='INGRESO',
                    fecha_registro__range=(inicio_h, fin_h),
                )
                .values_list('categoria_id', flat=True)
                .distinct()
            )
            for c_id in categorias_mes:
                apariciones[c_id] = apariciones.get(c_id, 0) + 1

        recurrentes = [c_id for c_id, veces in apariciones.items() if veces >= 3]
        fecha_limite = now - timezone.timedelta(days=UMBRAL_CONCEPTO_SIN_USO_DIAS)

        for c_id in recurrentes:
            tiene_recientes = Movimiento.objects.filter(
                usuario=usuario,
                tipo='INGRESO',
                categoria_id=c_id,
                fecha_registro__gte=fecha_limite,
            ).exists()

            if not tiene_recientes:
                from categorias.models import Categoria
                nombre = Categoria.objects.filter(pk=c_id).values_list('nombre', flat=True).first() or 'desconocida'
                _crear_notificacion(
                    usuario=usuario,
                    tipo=Notificacion.Tipo.CONCEPTO_SIN_USO,
                    titulo='Categoría recurrente sin actividad',
                    descripcion=(
                        f"No has registrado ingresos para '{nombre}' en los últimos "
                        f"{UMBRAL_CONCEPTO_SIN_USO_DIAS} días. ¿Olvidaste registrar algún ingreso?"
                    ),
                )
    except Exception as e:
        print(f'[notificaciones] Error en _check_concepto_sin_uso: {e}')


# ─── Alertas de tiempo ────────────────────────────────────────────────────────

def _check_velocidad_gasto(usuario, egreso):
    """
    Alerta cuando se ha gastado más del 70% de los ingresos
    antes del día 15 del mes.
    """
    try:
        from .models import Notificacion

        now    = timezone.now()
        dia    = now.day
        inicio = _inicio_mes(now)

        if dia > UMBRAL_VELOCIDAD_GASTO_DIA:
            return

        egresos  = _total_en_rango(usuario, 'EGRESO',  inicio, now)
        ingresos = _total_en_rango(usuario, 'INGRESO', inicio, now)

        if ingresos <= 0:
            return

        porcentaje = (egresos / ingresos * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if porcentaje >= UMBRAL_VELOCIDAD_GASTO_PCT:
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.VELOCIDAD_GASTO,
                titulo='Velocidad de gasto alta',
                descripcion=(
                    f'Has gastado el {porcentaje}% de tus ingresos (${egresos:,.2f} de '
                    f'${ingresos:,.2f}) y solo estamos en el día {dia} del mes. '
                    f'Modera tus gastos.'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_velocidad_gasto: {e}')


def _check_inactividad_ingresos(usuario, ingreso):
    """
    Alerta cuando han pasado más de N días desde el último ingreso registrado.
    """
    try:
        from movimientos.models import Movimiento
        from .models import Notificacion

        ultimo = (
            Movimiento.objects.filter(usuario=usuario, tipo='INGRESO')
            .exclude(pk=ingreso.pk)
            .order_by('-fecha_registro')
            .first()
        )
        if not ultimo:
            return

        dias = (timezone.now().date() - ultimo.fecha_registro.date()).days
        if dias >= UMBRAL_INACTIVIDAD_INGRESOS:
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.INACTIVIDAD_INGRESOS,
                titulo='Inactividad de ingresos',
                descripcion=(
                    f'Han pasado {dias} días desde tu último ingreso. '
                    f'¿Olvidaste registrar alguno?'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_inactividad_ingresos: {e}')


def _check_egresos_agrupados(usuario, egreso):
    """
    Alerta cuando se registran N o más egresos dentro de una ventana de X horas.
    """
    try:
        from .models import Notificacion

        now      = timezone.now()
        inicio   = now - timezone.timedelta(hours=UMBRAL_EGRESOS_AGRUPADOS_HORAS)
        cantidad = _count_en_rango(usuario, 'EGRESO', inicio, now)

        if cantidad >= UMBRAL_EGRESOS_AGRUPADOS_N:
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.EGRESOS_AGRUPADOS,
                titulo='Múltiples gastos en corto tiempo',
                descripcion=(
                    f'Has registrado {cantidad} egresos en las últimas '
                    f'{UMBRAL_EGRESOS_AGRUPADOS_HORAS} horas. '
                    f'¿Compras impulsivas? Revisa tus gastos.'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_egresos_agrupados: {e}')


# ─── Alertas de balance / ahorro ─────────────────────────────────────────────

def _check_balance_critico(usuario, egreso):
    """
    Proyecta el egreso al final del mes con el ritmo actual y alerta
    si el balance proyectado es negativo.
    """
    try:
        from .models import Notificacion

        now    = timezone.now()
        dia    = now.day
        inicio = _inicio_mes(now)

        import calendar
        dias_del_mes = calendar.monthrange(now.year, now.month)[1]

        egresos_mes = _total_en_rango(usuario, 'EGRESO', inicio, now)
        ingresos_totales = _total_en_rango(usuario, 'INGRESO', inicio, now)

        if dia <= 0 or ingresos_totales <= 0:
            return

        promedio_diario   = egresos_mes / dia
        egreso_proyectado = promedio_diario * dias_del_mes
        balance_proyectado = ingresos_totales - egreso_proyectado

        if balance_proyectado < 0:
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.DEFICIT,
                titulo='Balance crítico proyectado',
                descripcion=(
                    f'A tu ritmo actual de gasto (${promedio_diario:,.2f}/día), '
                    f'terminarás el mes con un saldo negativo de '
                    f'${abs(balance_proyectado):,.2f}. ¡Reduce tus egresos!'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_balance_critico: {e}')


# ─── Alertas de micro-gastos ──────────────────────────────────────────────────

def _check_micro_gastos(usuario, egreso):
    """
    Alerta cuando hay N o más egresos pequeños (menores al umbral) en el mes.
    """
    try:
        from movimientos.models import Movimiento
        from .models import Notificacion

        now    = timezone.now()
        inicio = _inicio_mes(now)

        micro = Movimiento.objects.filter(
            usuario=usuario,
            tipo='EGRESO',
            fecha_registro__range=(inicio, now),
            monto__lte=UMBRAL_MICRO_MONTO_MAX,
        )
        cantidad = micro.count()
        if cantidad >= UMBRAL_MICRO_CANTIDAD:
            total_micro = micro.aggregate(t=Sum('monto'))['t'] or Decimal('0')
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.MICRO_GASTOS,
                titulo='Múltiples micro-gastos detectados',
                descripcion=(
                    f'Has registrado {cantidad} gastos pequeños '
                    f'(menores a ${UMBRAL_MICRO_MONTO_MAX:,.2f}) que suman '
                    f'${total_micro:,.2f} este mes. La "muerte por mil cortes".'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_micro_gastos: {e}')


def _check_gastos_hormiga(usuario, egreso):
    """
    Alerta cuando el total de egresos del día supera el umbral y
    hay al menos 3 transacciones (gastos hormiga acumulados).
    """
    try:
        from .models import Notificacion

        now       = timezone.now()
        inicio_hoy = now.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_hoy    = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        gasto_hoy = _total_en_rango(usuario, 'EGRESO', inicio_hoy, fin_hoy)
        if gasto_hoy < UMBRAL_HORMIGA_MONTO_DIA:
            return

        cantidad = _count_en_rango(usuario, 'EGRESO', inicio_hoy, fin_hoy)
        if cantidad >= UMBRAL_HORMIGA_TRANSACCIONES:
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.GASTOS_HORMIGA,
                titulo='Gastos hormiga diarios',
                descripcion=(
                    f'Hoy has gastado ${gasto_hoy:,.2f} en pequeños gastos '
                    f'({cantidad} transacciones). '
                    f'Estos gastos hormiga se acumulan rápidamente.'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_gastos_hormiga: {e}')


# ─── Alertas predictivas ──────────────────────────────────────────────────────

def _check_proyeccion_sobregasto(usuario, egreso):
    """
    Proyecta el gasto al final del mes y alerta si superará los ingresos.
    """
    try:
        from .models import Notificacion
        import calendar

        now    = timezone.now()
        dia    = now.day
        inicio = _inicio_mes(now)

        egresos  = _total_en_rango(usuario, 'EGRESO',  inicio, now)
        ingresos = _total_en_rango(usuario, 'INGRESO', inicio, now)

        if dia <= 0 or ingresos <= 0:
            return

        dias_restantes    = calendar.monthrange(now.year, now.month)[1] - dia
        promedio_diario   = egresos / dia
        egreso_proyectado = egresos + promedio_diario * dias_restantes

        if egreso_proyectado > ingresos:
            sobregasto = egreso_proyectado - ingresos
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.PROYECCION_SOBREGASTO,
                titulo='Proyección de sobregasto',
                descripcion=(
                    f'Al ritmo actual (${promedio_diario:,.2f}/día), gastarás '
                    f'${egreso_proyectado:,.2f} este mes, superando tus ingresos '
                    f'(${ingresos:,.2f}) por ${sobregasto:,.2f}.'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_proyeccion_sobregasto: {e}')


def _check_comparacion_periodo_egresos(usuario, egreso):
    """
    Alerta si los egresos del mes actual cambiaron más del umbral
    respecto al mes anterior (tanto aumento como reducción significativa).
    """
    try:
        from .models import Notificacion

        now            = timezone.now()
        inicio_actual  = _inicio_mes(now)
        egresos_actual = _total_en_rango(usuario, 'EGRESO', inicio_actual, now)

        # mes anterior completo
        primer_dia_actual  = now.replace(day=1)
        ultimo_dia_anterior = primer_dia_actual - timezone.timedelta(days=1)
        inicio_anterior = _inicio_mes(ultimo_dia_anterior)
        fin_anterior    = _fin_mes(ultimo_dia_anterior)
        egresos_anterior = _total_en_rango(usuario, 'EGRESO', inicio_anterior, fin_anterior)

        if egresos_anterior <= 0:
            return

        diferencia = egresos_actual - egresos_anterior
        cambio = (diferencia / egresos_anterior * 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        if abs(cambio) >= UMBRAL_COMPARACION_PERIODO_PCT:
            if cambio > 0:
                descripcion = (
                    f'Has gastado un {cambio}% MÁS este mes (${egresos_actual:,.2f}) '
                    f'comparado con el mes pasado (${egresos_anterior:,.2f}).'
                )
            else:
                descripcion = (
                    f'¡Bien! Has gastado un {abs(cambio)}% MENOS este mes '
                    f'(${egresos_actual:,.2f}) comparado con el mes pasado '
                    f'(${egresos_anterior:,.2f}). ¡Sigue así!'
                )
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.COMPARACION_PERIODO,
                titulo='Comparación con mes anterior',
                descripcion=descripcion,
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_comparacion_periodo_egresos: {e}')


def _check_dia_mes_critico(usuario, egreso):
    """
    Alerta cuando ya se gastó un porcentaje crítico de los ingresos
    en relación al día del mes en que estamos.
    """
    try:
        from .models import Notificacion

        now    = timezone.now()
        dia    = now.day
        inicio = _inicio_mes(now)

        egresos  = _total_en_rango(usuario, 'EGRESO',  inicio, now)
        ingresos = _total_en_rango(usuario, 'INGRESO', inicio, now)

        if ingresos <= 0:
            return

        porcentaje = (egresos / ingresos * 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        if porcentaje >= UMBRAL_DIA_MES_CRITICO_PCT:
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.DIA_MES_CRITICO,
                titulo='Día del mes crítico',
                descripcion=(
                    f'Estamos a día {dia} del mes y ya gastaste el {porcentaje}% '
                    f'de tus ingresos (${egresos:,.2f} de ${ingresos:,.2f}).'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_dia_mes_critico: {e}')


# ─── Alertas de inconsistencias ───────────────────────────────────────────────

def _check_egreso_sin_concepto(usuario, egreso):
    """
    Alerta cuando hay N o más egresos sin concepto asignado.
    """
    try:
        from movimientos.models import Movimiento
        from .models import Notificacion

        cantidad = Movimiento.objects.filter(
            usuario=usuario,
            tipo='EGRESO',
            descripcion__isnull=True,
        ).count()

        if cantidad >= UMBRAL_EGRESOS_SIN_CONCEPTO:
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.EGRESO_SIN_CONCEPTO,
                titulo='Egresos sin categorizar',
                descripcion=(
                    f'Tienes {cantidad} egresos sin concepto asignado. '
                    f'Categorízalos para un mejor análisis de tus gastos.'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_egreso_sin_concepto: {e}')


def _check_ingreso_inusual(usuario, ingreso):
    """
    Alerta cuando un ingreso individual supera N veces el promedio
    mensual de los últimos 6 meses.
    """
    try:
        from .models import Notificacion

        now  = timezone.now()
        suma = Decimal('0')
        meses_con_datos = 0

        for i in range(1, 7):
            mes_dt = now.replace(day=1)
            for _ in range(i):
                mes_dt = (mes_dt - timezone.timedelta(days=1)).replace(day=1)
            inicio_h = _inicio_mes(mes_dt)
            fin_h    = _fin_mes(mes_dt)
            total    = _total_en_rango(usuario, 'INGRESO', inicio_h, fin_h)
            if total > 0:
                suma += total
                meses_con_datos += 1

        if meses_con_datos == 0 or suma <= 0:
            return

        promedio = (suma / meses_con_datos).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        umbral   = promedio * UMBRAL_INGRESO_INUSUAL_MULT

        if ingreso.monto >= umbral:
            _crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.Tipo.INGRESO_INUSUAL,
                titulo='Ingreso inusualmente alto',
                descripcion=(
                    f'Registraste un ingreso de ${ingreso.monto:,.2f}, '
                    f'significativamente mayor a tu promedio mensual (${promedio:,.2f}). '
                    f'Verifica que sea correcto.'
                ),
            )
    except Exception as e:
        print(f'[notificaciones] Error en _check_ingreso_inusual: {e}')
        
        


# from decimal import Decimal


# def crear_notificacion(usuario, tipo, titulo, descripcion):
#     """
#     Crea una notificación para el usuario si no existe una igual no leída.
#     Evita duplicar notificaciones del mismo tipo en el mismo día.

#     Args:
#         usuario: instancia del usuario.
#         tipo (str): tipo de notificación definido en Notificacion.Tipo.
#         titulo (str): título corto de la notificación.
#         descripcion (str): detalle de la notificación.
#     """
#     from .models import Notificacion
#     from django.utils import timezone

#     hoy = timezone.now().date()

#     ya_existe = Notificacion.objects.filter(
#         usuario=usuario,
#         tipo=tipo,
#         leida=False,
#         fecha_creacion__date=hoy
#     ).exists()

#     if not ya_existe:
#         Notificacion.objects.create(
#             usuario=usuario,
#             tipo=tipo,
#             titulo=titulo,
#             descripcion=descripcion
#         )


# def analizar_movimiento(usuario, mes, anio, ultimo_egreso=None):
#     """
#     Analiza el estado financiero del usuario tras un movimiento
#     y genera notificaciones según corresponda.

#     Reglas aplicadas:
#     - UMBRAL_MENSUAL: se dispara cuando los egresos superan el umbral
#       configurado en las preferencias del usuario.
#     - DEFICIT: se dispara cuando los egresos superan los ingresos del mes.
#     - EGRESO_GRANDE: se dispara cuando un egreso individual supera el
#       porcentaje configurado respecto al total de ingresos del mes.

#     Args:
#         usuario: instancia del usuario.
#         mes (int): mes del movimiento registrado.
#         anio (int): año del movimiento registrado.
#         ultimo_egreso (Decimal): monto del último egreso registrado, opcional.
#     """
#     from dashboard.models import ResumenMensual
#     from .models import Notificacion

#     resumen = ResumenMensual.objects.filter(
#         usuario=usuario,
#         mes=mes,
#         anio=anio
#     ).first()

#     if not resumen:
#         return

#     try:
#         preferencias = usuario.preferencias
#     except Exception:
#         return

#     # Notificacion: umbral mensual alcanzado
#     if (preferencias.alerta_presupuesto
#             and resumen.total_ingresos > 0):
#         porcentaje_gastado = (resumen.total_egresos / resumen.total_ingresos) * 100
#         if porcentaje_gastado >= preferencias.umbral_advertencia_porcentaje:
#             crear_notificacion(
#                 usuario=usuario,
#                 tipo=Notificacion.Tipo.UMBRAL_MENSUAL,
#                 titulo='Umbral de gastos alcanzado',
#                 descripcion=(
#                     f'Has gastado el {porcentaje_gastado:.1f}% de tus ingresos '
#                     f'de este mes (${resumen.total_egresos:,.2f} de '
#                     f'${resumen.total_ingresos:,.2f}).'
#                 )
#             )

#     # Notificacion: deficit
#     if preferencias.alerta_deficit and resumen.deficit:
#         crear_notificacion(
#             usuario=usuario,
#             tipo=Notificacion.Tipo.DEFICIT,
#             titulo='Balance en déficit',
#             descripcion=(
#                 f'Tus egresos (${resumen.total_egresos:,.2f}) superan '
#                 f'tus ingresos (${resumen.total_ingresos:,.2f}) este mes.'
#             )
#         )

#     # Notificacion: egreso grande
#     if (preferencias.alerta_egreso_grande
#             and ultimo_egreso is not None
#             and resumen.total_ingresos > 0):
#         porcentaje_egreso = (ultimo_egreso / resumen.total_ingresos) * 100
#         if porcentaje_egreso >= preferencias.egreso_grande_porcentaje:
#             crear_notificacion(
#                 usuario=usuario,
#                 tipo=Notificacion.Tipo.EGRESO_GRANDE,
#                 titulo='Egreso grande registrado',
#                 descripcion=(
#                     f'Registraste un egreso de ${ultimo_egreso:,.2f} que representa '
#                     f'el {porcentaje_egreso:.1f}% de tus ingresos del mes.'
#                 )
#             )