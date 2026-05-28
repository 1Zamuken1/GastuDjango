from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from notificaciones.models import Notificacion
from notificaciones.checks.query_helpers import count_en_rango, total_en_rango, fin_mes

class CheckBase:
    def __init__(self, ctx, movimiento):
        self.ctx = ctx
        self.movimiento = movimiento
        if hasattr(self.movimiento, 'monto') and not isinstance(self.movimiento.monto, Decimal):
            self.movimiento.monto = Decimal(str(self.movimiento.monto))
        self.prefs = ctx.preferencias

    def is_enabled(self):
        return True

    def run(self):
        raise NotImplementedError

    def crear_alerta(self, tipo, titulo, descripcion):
        return {
            'tipo': tipo,
            'titulo': titulo,
            'descripcion': descripcion,
            'referencia_id': self.movimiento.id,
            'referencia_tipo': 'movimiento'
        }

class CheckUmbralMensual(CheckBase):
    def run(self):
        if self.ctx.total_ingresos_mes <= 0:
            return None
        porcentaje = (self.ctx.total_egresos_mes / self.ctx.total_ingresos_mes * 100).quantize(
            Decimal('0.1'), rounding=ROUND_HALF_UP
        )
        umbral_pref = Decimal(str(self.prefs.umbral_advertencia_porcentaje))
        if porcentaje >= umbral_pref:
            return self.crear_alerta(
                Notificacion.Tipo.UMBRAL_MENSUAL,
                'Umbral de gastos alcanzado',
                f'Has gastado el {porcentaje}% de tus ingresos de este mes (${self.ctx.total_egresos_mes:,.2f} de ${self.ctx.total_ingresos_mes:,.2f}).'
            )

class CheckDeficit(CheckBase):
    def run(self):
        if self.ctx.total_egresos_mes > self.ctx.total_ingresos_mes:
            return self.crear_alerta(
                Notificacion.Tipo.DEFICIT,
                'Balance en déficit',
                f'Tus egresos (${self.ctx.total_egresos_mes:,.2f}) superan tus ingresos (${self.ctx.total_ingresos_mes:,.2f}) este mes.'
            )

class CheckEgresoGrande(CheckBase):
    def is_enabled(self):
        return self.prefs.alerta_egreso_grande_activa

    def run(self):
        if self.ctx.total_ingresos_mes <= 0:
            return None
        porcentaje = (self.movimiento.monto / self.ctx.total_ingresos_mes * 100).quantize(
            Decimal('0.1'), rounding=ROUND_HALF_UP
        )
        umbral_pref = Decimal(str(self.prefs.egreso_grande_porcentaje))
        if porcentaje >= umbral_pref:
            return self.crear_alerta(
                Notificacion.Tipo.EGRESO_GRANDE,
                'Egreso grande registrado',
                f'Registraste un egreso de ${self.movimiento.monto:,.2f} que representa el {porcentaje}% de tus ingresos del mes.'
            )

class CheckGastoIncremental(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_gasto_incremental_enabled

    def run(self):
        now = self.ctx.now
        meses = self.prefs.alert_gasto_incremental_meses
        suma_historica = Decimal('0')
        
        for i in range(1, meses + 1):
            mes_dt = (now.replace(day=1) - timezone.timedelta(days=1)).replace(day=1)
            for _ in range(i - 1):
                mes_dt = (mes_dt.replace(day=1) - timezone.timedelta(days=1)).replace(day=1)
            
            inicio_h = mes_dt
            fin_h = fin_mes(mes_dt)
            suma_historica += total_en_rango(self.ctx.usuario, 'EGRESO', inicio_h, fin_h)

        if suma_historica <= 0:
            return None

        promedio = (suma_historica / meses).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if promedio <= 0:
            return None

        incremento = ((self.ctx.total_egresos_mes - promedio) / promedio * 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        umbral_pref = Decimal(str(self.prefs.alert_gasto_incremental_porcentaje))
        if incremento >= umbral_pref:
            return self.crear_alerta(
                Notificacion.Tipo.GASTO_INCREMENTAL,
                'Gasto incremental detectado',
                f'Tus egresos este mes (${self.ctx.total_egresos_mes:,.2f}) superan el promedio de los últimos {meses} meses (${promedio:,.2f}) en un {incremento}%. Considera revisar tus gastos.'
            )

class CheckPatronInusualEgresos(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_patron_inusual_enabled

    def run(self):
        now = self.ctx.now
        inicio_hoy = now.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_hoy = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        transacciones_hoy = count_en_rango(self.ctx.usuario, 'EGRESO', inicio_hoy, fin_hoy)
        dias_del_mes = (now.date() - self.ctx.inicio_mes.date()).days + 1
        transacciones_mes = count_en_rango(self.ctx.usuario, 'EGRESO', self.ctx.inicio_mes, fin_hoy)

        if dias_del_mes <= 0:
            return None

        promedio_diario = transacciones_mes / dias_del_mes
        if transacciones_hoy > promedio_diario * 2 and transacciones_hoy >= 8:
            return self.crear_alerta(
                Notificacion.Tipo.PATRON_INUSUAL,
                'Patrón inusual de gastos',
                f'Hoy has registrado {transacciones_hoy} egresos, significativamente más que tu promedio diario ({promedio_diario:.1f}). Verifica que no haya errores.'
            )

class CheckConcentracionGastos(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_concentracion_gastos_enabled

    def run(self):
        if self.ctx.total_egresos_mes <= 0:
            return None
            
        from movimientos.models import Movimiento
        from django.db.models import Sum
        
        stats = (
            Movimiento.objects.filter(
                usuario=self.ctx.usuario,
                tipo='EGRESO',
                fecha_registro__range=(self.ctx.inicio_mes, self.ctx.now),
            )
            .values('categoria', 'categoria__nombre')
            .annotate(total=Sum('monto'))
        )

        for stat in stats:
            total_concepto = Decimal(str(stat['total'])) if stat['total'] else Decimal('0')
            porcentaje = (total_concepto / self.ctx.total_egresos_mes * 100).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            umbral_pref = Decimal(str(self.prefs.alert_concentracion_gastos_porcentaje))
            if porcentaje >= umbral_pref:
                return self.crear_alerta(
                    Notificacion.Tipo.CONCENTRACION_GASTO,
                    'Concentración de gastos en una categoría',
                    f"La categoría '{stat['categoria__nombre']}' representa el {porcentaje}% de tus egresos este mes (${total_concepto:,.2f} de ${self.ctx.total_egresos_mes:,.2f}). Considera diversificar."
                )

class CheckVelocidadGasto(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_velocidad_gasto_enabled

    def run(self):
        dia = self.ctx.now.day
        # TODO: Move day 15 config to prefs if needed, hardcoded in original
        if dia > 15: 
            return None

        if self.ctx.total_ingresos_mes <= 0:
            return None

        porcentaje = (self.ctx.total_egresos_mes / self.ctx.total_ingresos_mes * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if porcentaje >= 70: # Hardcoded in original, we can leave it or move to prefs
            return self.crear_alerta(
                Notificacion.Tipo.VELOCIDAD_GASTO,
                'Velocidad de gasto alta',
                f'Has gastado el {porcentaje}% de tus ingresos (${self.ctx.total_egresos_mes:,.2f} de ${self.ctx.total_ingresos_mes:,.2f}) y solo estamos en el día {dia} del mes. Modera tus gastos.'
            )

class CheckEgresosAgrupados(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_egresos_agrupados_enabled

    def run(self):
        horas = self.prefs.alert_egresos_agrupados_horas
        inicio = self.ctx.now - timezone.timedelta(hours=horas)
        cantidad = count_en_rango(self.ctx.usuario, 'EGRESO', inicio, self.ctx.now)

        if cantidad >= self.prefs.alert_egresos_agrupados_cantidad:
            return self.crear_alerta(
                Notificacion.Tipo.EGRESOS_AGRUPADOS,
                'Múltiples gastos en corto tiempo',
                f'Has registrado {cantidad} egresos en las últimas {horas} horas. ¿Compras impulsivas? Revisa tus gastos.'
            )

class CheckBalanceCritico(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_balance_critico_enabled

    def run(self):
        dia = self.ctx.now.day
        if dia <= 0 or self.ctx.total_ingresos_mes <= 0:
            return None

        promedio_diario = self.ctx.total_egresos_mes / dia
        egreso_proyectado = promedio_diario * self.ctx.dias_del_mes
        balance_proyectado = self.ctx.total_ingresos_mes - egreso_proyectado

        if balance_proyectado < 0:
            return self.crear_alerta(
                Notificacion.Tipo.DEFICIT,
                'Balance crítico proyectado',
                f'A tu ritmo actual de gasto (${promedio_diario:,.2f}/día), terminarás el mes con un saldo negativo de ${abs(balance_proyectado):,.2f}. ¡Reduce tus egresos!'
            )

class CheckMicroGastos(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_micro_gastos_enabled

    def run(self):
        from movimientos.models import Movimiento
        from django.db.models import Sum
        
        micro = Movimiento.objects.filter(
            usuario=self.ctx.usuario,
            tipo='EGRESO',
            fecha_registro__range=(self.ctx.inicio_mes, self.ctx.now),
            monto__lte=self.prefs.alert_micro_gastos_monto_max,
        )
        cantidad = micro.count()
        if cantidad >= self.prefs.alert_micro_gastos_cantidad:
            t = micro.aggregate(t=Sum('monto'))['t']
            total_micro = Decimal(str(t)) if t else Decimal('0')
            return self.crear_alerta(
                Notificacion.Tipo.MICRO_GASTOS,
                'Múltiples micro-gastos detectados',
                f'Has registrado {cantidad} gastos pequeños (menores a ${self.prefs.alert_micro_gastos_monto_max:,.2f}) que suman ${total_micro:,.2f} este mes. La "muerte por mil cortes".'
            )

class CheckGastosHormiga(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_gastos_hormiga_enabled

    def run(self):
        inicio_hoy = self.ctx.now.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_hoy = self.ctx.now.replace(hour=23, minute=59, second=59, microsecond=999999)

        gasto_hoy = total_en_rango(self.ctx.usuario, 'EGRESO', inicio_hoy, fin_hoy)
        umbral_pref = Decimal(str(self.prefs.alert_gastos_hormiga_monto_dia))
        if gasto_hoy < umbral_pref:
            return None

        cantidad = count_en_rango(self.ctx.usuario, 'EGRESO', inicio_hoy, fin_hoy)
        if cantidad >= 3: # Hardcoded min transactions in original
            return self.crear_alerta(
                Notificacion.Tipo.GASTOS_HORMIGA,
                'Gastos hormiga diarios',
                f'Hoy has gastado ${gasto_hoy:,.2f} en pequeños gastos ({cantidad} transacciones). Estos gastos hormiga se acumulan rápidamente.'
            )

class CheckProyeccionSobregasto(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_proyeccion_sobregasto_enabled

    def run(self):
        dia = self.ctx.now.day
        if dia <= 0 or self.ctx.total_ingresos_mes <= 0:
            return None

        dias_restantes = self.ctx.dias_del_mes - dia
        promedio_diario = self.ctx.total_egresos_mes / dia
        egreso_proyectado = self.ctx.total_egresos_mes + (promedio_diario * dias_restantes)

        if egreso_proyectado > self.ctx.total_ingresos_mes:
            sobregasto = egreso_proyectado - self.ctx.total_ingresos_mes
            return self.crear_alerta(
                Notificacion.Tipo.PROYECCION_SOBREGASTO,
                'Proyección de sobregasto',
                f'Al ritmo actual (${promedio_diario:,.2f}/día), gastarás ${egreso_proyectado:,.2f} este mes, superando tus ingresos (${self.ctx.total_ingresos_mes:,.2f}) por ${sobregasto:,.2f}.'
            )

class CheckComparacionPeriodoEgresos(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_comparacion_periodo_enabled

    def run(self):
        now = self.ctx.now
        primer_dia_actual = now.replace(day=1)
        ultimo_dia_anterior = primer_dia_actual - timezone.timedelta(days=1)
        inicio_anterior = ultimo_dia_anterior.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fin_anterior = fin_mes(ultimo_dia_anterior)
        
        egresos_anterior = total_en_rango(self.ctx.usuario, 'EGRESO', inicio_anterior, fin_anterior)

        if egresos_anterior <= 0:
            return None

        diferencia = self.ctx.total_egresos_mes - egresos_anterior
        cambio = (diferencia / egresos_anterior * 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        # Hardcoded 20% umbral in original
        if abs(cambio) >= 20: 
            if cambio > 0:
                descripcion = f'Has gastado un {cambio}% MÁS este mes (${self.ctx.total_egresos_mes:,.2f}) comparado con el mes pasado (${egresos_anterior:,.2f}).'
            else:
                descripcion = f'¡Bien! Has gastado un {abs(cambio)}% MENOS este mes (${self.ctx.total_egresos_mes:,.2f}) comparado con el mes pasado (${egresos_anterior:,.2f}). ¡Sigue así!'
            
            return self.crear_alerta(
                Notificacion.Tipo.COMPARACION_PERIODO,
                'Comparación con mes anterior',
                descripcion
            )

class CheckDiaMesCritico(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_dia_mes_critico_enabled

    def run(self):
        if self.ctx.total_ingresos_mes <= 0:
            return None

        porcentaje = (self.ctx.total_egresos_mes / self.ctx.total_ingresos_mes * 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        umbral_pref = Decimal(str(self.prefs.alert_dia_mes_critico_porcentaje))
        if porcentaje >= umbral_pref:
            return self.crear_alerta(
                Notificacion.Tipo.DIA_MES_CRITICO,
                'Día del mes crítico',
                f'Estamos a día {self.ctx.now.day} del mes y ya gastaste el {porcentaje}% de tus ingresos (${self.ctx.total_egresos_mes:,.2f} de ${self.ctx.total_ingresos_mes:,.2f}).'
            )

class CheckEgresoSinConcepto(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_egreso_sin_concepto_enabled

    def run(self):
        from movimientos.models import Movimiento
        cantidad = Movimiento.objects.filter(
            usuario=self.ctx.usuario,
            tipo='EGRESO',
            descripcion__isnull=True,
        ).count()

        if cantidad >= self.prefs.alert_egreso_sin_concepto_cantidad:
            return self.crear_alerta(
                Notificacion.Tipo.EGRESO_SIN_CONCEPTO,
                'Egresos sin categorizar',
                f'Tienes {cantidad} egresos sin concepto asignado. Categorízalos para un mejor análisis de tus gastos.'
            )
