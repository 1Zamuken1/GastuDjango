from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from notificaciones.models import Notificacion
from notificaciones.checks.query_helpers import count_en_rango, total_en_rango, fin_mes
from notificaciones.checks.egreso_checks import CheckBase

class CheckReduccionIngresos(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_reduccion_ingresos_enabled

    def run(self):
        now = self.ctx.now
        suma_historica = Decimal('0')
        
        for i in range(1, 4):
            mes_dt = now.replace(day=1)
            for _ in range(i):
                mes_dt = (mes_dt - timezone.timedelta(days=1)).replace(day=1)
            inicio_h = mes_dt
            fin_h = fin_mes(mes_dt)
            suma_historica += total_en_rango(self.ctx.usuario, 'INGRESO', inicio_h, fin_h)

        if suma_historica <= 0:
            return None

        promedio = (suma_historica / 3).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        reduccion = ((promedio - self.ctx.total_ingresos_mes) / promedio * 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        umbral_pref = Decimal(str(self.prefs.alert_reduccion_ingresos_porcentaje))
        if reduccion >= umbral_pref:
            return self.crear_alerta(
                Notificacion.Tipo.REDUCCION_INGRESOS,
                'Reducción de ingresos detectada',
                f'Tus ingresos este mes (${self.ctx.total_ingresos_mes:,.2f}) son un {reduccion}% menores al promedio de los últimos 3 meses (${promedio:,.2f}).'
            )

class CheckInactividadIngresos(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_inactividad_ingresos_enabled

    def run(self):
        from movimientos.models import Movimiento
        ultimo = (
            Movimiento.objects.filter(usuario=self.ctx.usuario, tipo='INGRESO')
            .exclude(pk=self.movimiento.pk)
            .order_by('-fecha_registro')
            .first()
        )
        if not ultimo:
            return None

        dias = (self.ctx.now.date() - ultimo.fecha_registro.date()).days
        if dias >= self.prefs.alert_inactividad_dias:
            return self.crear_alerta(
                Notificacion.Tipo.INACTIVIDAD_INGRESOS,
                'Inactividad de ingresos',
                f'Han pasado {dias} días desde tu último ingreso. ¿Olvidaste registrar alguno?'
            )

class CheckIngresoInusual(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_ingreso_inusual_enabled

    def run(self):
        now = self.ctx.now
        suma = Decimal('0')
        meses_con_datos = 0

        for i in range(1, 7):
            mes_dt = now.replace(day=1)
            for _ in range(i):
                mes_dt = (mes_dt - timezone.timedelta(days=1)).replace(day=1)
            inicio_h = mes_dt
            fin_h = fin_mes(mes_dt)
            total = total_en_rango(self.ctx.usuario, 'INGRESO', inicio_h, fin_h)
            if total > 0:
                suma += total
                meses_con_datos += 1

        if meses_con_datos == 0 or suma <= 0:
            return None

        promedio = (suma / meses_con_datos).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        multiplicador = Decimal(str(self.prefs.alert_ingreso_inusual_multiplicador))
        umbral = promedio * multiplicador

        if self.movimiento.monto >= umbral:
            return self.crear_alerta(
                Notificacion.Tipo.INGRESO_INUSUAL,
                'Ingreso inusualmente alto',
                f'Registraste un ingreso de ${self.movimiento.monto:,.2f}, significativamente mayor a tu promedio mensual (${promedio:,.2f}). Verifica que sea correcto.'
            )

class CheckConceptoSinUso(CheckBase):
    def is_enabled(self):
        return self.prefs.alert_concepto_sin_uso_enabled

    def run(self):
        from movimientos.models import Movimiento
        now = self.ctx.now
        apariciones = {}

        for i in range(1, 7):
            mes_dt = now.replace(day=1)
            for _ in range(i):
                mes_dt = (mes_dt - timezone.timedelta(days=1)).replace(day=1)
            inicio_h = mes_dt
            fin_h = fin_mes(mes_dt)

            categorias_mes = (
                Movimiento.objects.filter(
                    usuario=self.ctx.usuario,
                    tipo='INGRESO',
                    fecha_registro__range=(inicio_h, fin_h),
                )
                .values_list('categoria_id', flat=True)
                .distinct()
            )
            for c_id in categorias_mes:
                if c_id:
                    apariciones[c_id] = apariciones.get(c_id, 0) + 1

        recurrentes = [c_id for c_id, veces in apariciones.items() if veces >= 3]
        fecha_limite = now - timezone.timedelta(days=self.prefs.alert_concepto_sin_uso_dias)

        for c_id in recurrentes:
            tiene_recientes = Movimiento.objects.filter(
                usuario=self.ctx.usuario,
                tipo='INGRESO',
                categoria_id=c_id,
                fecha_registro__gte=fecha_limite,
            ).exists()

            if not tiene_recientes:
                from categorias.models import Categoria
                nombre = Categoria.objects.filter(pk=c_id).values_list('nombre', flat=True).first() or 'desconocida'
                return self.crear_alerta(
                    Notificacion.Tipo.CONCEPTO_SIN_USO,
                    'Categoría recurrente sin actividad',
                    f"No has registrado ingresos para '{nombre}' en los últimos {self.prefs.alert_concepto_sin_uso_dias} días. ¿Olvidaste registrar algún ingreso?"
                )
        return None
