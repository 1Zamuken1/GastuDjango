from django import forms
from .models import PreferenciasAlertas

class PreferenciasAlertasForm(forms.ModelForm):
    class Meta:
        model = PreferenciasAlertas
        fields = [
            'umbral_advertencia_porcentaje',
            'egreso_grande_porcentaje',
            'alerta_egreso_grande_activa',
            
            'alert_gasto_incremental_enabled',
            'alert_gasto_incremental_porcentaje',
            'alert_gasto_incremental_meses',
            'alert_reduccion_ingresos_enabled',
            'alert_reduccion_ingresos_porcentaje',
            'alert_patron_inusual_enabled',
            
            'alert_concentracion_gastos_enabled',
            'alert_concentracion_gastos_porcentaje',
            'alert_concepto_sin_uso_enabled',
            'alert_concepto_sin_uso_dias',
            
            'alert_velocidad_gasto_enabled',
            'alert_inactividad_ingresos_enabled',
            'alert_inactividad_dias',
            'alert_egresos_agrupados_enabled',
            'alert_egresos_agrupados_cantidad',
            'alert_egresos_agrupados_horas',
            
            'meta_ahorro_mensual',
            'alert_meta_ahorro_enabled',
            'alert_balance_critico_enabled',
            'alert_recordatorio_ahorro_enabled',
            'alert_recordatorio_ahorro_dias',
            
            'alert_micro_gastos_enabled',
            'alert_micro_gastos_cantidad',
            'alert_micro_gastos_monto_max',
            'alert_gastos_hormiga_enabled',
            'alert_gastos_hormiga_monto_dia',
            
            'alert_proyeccion_sobregasto_enabled',
            'alert_comparacion_periodo_enabled',
            'alert_dia_mes_critico_enabled',
            'alert_dia_mes_critico_porcentaje',
            
            'alert_egreso_sin_concepto_enabled',
            'alert_egreso_sin_concepto_cantidad',
            'alert_ingreso_inusual_enabled',
            'alert_ingreso_inusual_multiplicador',
        ]
