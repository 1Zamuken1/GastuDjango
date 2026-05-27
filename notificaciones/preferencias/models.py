from django.db import models
from django.conf import settings

class PreferenciasAlertas(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prefs_alertas'
    )
    
    # ALERTAS GENERALES
    umbral_advertencia_porcentaje = models.PositiveSmallIntegerField(default=80)
    egreso_grande_porcentaje = models.PositiveSmallIntegerField(default=30)
    alerta_egreso_grande_activa = models.BooleanField(default=True)
    
    # TENDENCIAS
    alert_gasto_incremental_enabled = models.BooleanField(default=True)
    alert_gasto_incremental_porcentaje = models.PositiveSmallIntegerField(default=25)
    alert_gasto_incremental_meses = models.PositiveSmallIntegerField(default=3)
    alert_reduccion_ingresos_enabled = models.BooleanField(default=True)
    alert_reduccion_ingresos_porcentaje = models.PositiveSmallIntegerField(default=20)
    alert_patron_inusual_enabled = models.BooleanField(default=True)
    
    # CONCEPTOS / CATEGORÍAS
    alert_concentracion_gastos_enabled = models.BooleanField(default=True)
    alert_concentracion_gastos_porcentaje = models.PositiveSmallIntegerField(default=50)
    alert_concepto_sin_uso_enabled = models.BooleanField(default=False)
    alert_concepto_sin_uso_dias = models.PositiveSmallIntegerField(default=30)
    
    # TIEMPO
    alert_velocidad_gasto_enabled = models.BooleanField(default=True)
    alert_inactividad_ingresos_enabled = models.BooleanField(default=True)
    alert_inactividad_dias = models.PositiveSmallIntegerField(default=7)
    alert_egresos_agrupados_enabled = models.BooleanField(default=True)
    alert_egresos_agrupados_cantidad = models.PositiveSmallIntegerField(default=5)
    alert_egresos_agrupados_horas = models.PositiveSmallIntegerField(default=2)
    
    meta_ahorro_mensual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    alert_meta_ahorro_enabled = models.BooleanField(default=False)
    alert_balance_critico_enabled = models.BooleanField(default=True)
    alert_recordatorio_ahorro_enabled = models.BooleanField(
        default=True,
        verbose_name="Recordatorio de Cuota de Ahorro",
        help_text="Te avisaremos cuando se acerque la fecha de pago de tus ahorros."
    )
    alert_recordatorio_ahorro_dias = models.PositiveSmallIntegerField(
        default=3,
        verbose_name="Días de anticipación para recordatorios",
        help_text="Cuántos días antes de la fecha límite quieres recibir el aviso."
    )
    
    # MICRO-GASTOS
    alert_micro_gastos_enabled = models.BooleanField(default=True)
    alert_micro_gastos_cantidad = models.PositiveSmallIntegerField(default=10)
    alert_micro_gastos_monto_max = models.DecimalField(max_digits=12, decimal_places=2, default=10000)
    alert_gastos_hormiga_enabled = models.BooleanField(default=True)
    alert_gastos_hormiga_monto_dia = models.DecimalField(max_digits=12, decimal_places=2, default=50000)
    
    # PREDICTIVAS
    alert_proyeccion_sobregasto_enabled = models.BooleanField(default=True)
    alert_comparacion_periodo_enabled = models.BooleanField(default=True)
    alert_dia_mes_critico_enabled = models.BooleanField(default=True)
    alert_dia_mes_critico_porcentaje = models.PositiveSmallIntegerField(default=70)
    
    # INCONSISTENCIAS
    alert_egreso_sin_concepto_enabled = models.BooleanField(default=False)
    alert_egreso_sin_concepto_cantidad = models.PositiveSmallIntegerField(default=5)
    alert_ingreso_inusual_enabled = models.BooleanField(default=True)
    alert_ingreso_inusual_multiplicador = models.DecimalField(max_digits=4, decimal_places=2, default=2.5)

    class Meta:
        verbose_name = 'Preferencias de Alerta'
        verbose_name_plural = 'Preferencias de Alertas'

    def __str__(self):
        return f'Preferencias de {self.usuario.username}'
