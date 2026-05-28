from dataclasses import dataclass
from decimal import Decimal

@dataclass
class PrefsDTO:
    # ALERTAS GENERALES
    umbral_advertencia_porcentaje: int = 80
    egreso_grande_porcentaje: int = 30
    alerta_egreso_grande_activa: bool = True
    
    # TENDENCIAS
    alert_gasto_incremental_enabled: bool = True
    alert_gasto_incremental_porcentaje: int = 25
    alert_gasto_incremental_meses: int = 3
    alert_reduccion_ingresos_enabled: bool = True
    alert_reduccion_ingresos_porcentaje: int = 20
    alert_patron_inusual_enabled: bool = True
    
    # CONCEPTOS / CATEGORÍAS
    alert_concentracion_gastos_enabled: bool = True
    alert_concentracion_gastos_porcentaje: int = 50
    alert_concepto_sin_uso_enabled: bool = False
    alert_concepto_sin_uso_dias: int = 30
    
    # TIEMPO
    alert_velocidad_gasto_enabled: bool = True
    alert_inactividad_ingresos_enabled: bool = True
    alert_inactividad_dias: int = 7
    alert_egresos_agrupados_enabled: bool = True
    alert_egresos_agrupados_cantidad: int = 5
    alert_egresos_agrupados_horas: int = 2
    
    # AHORRO / BALANCE
    meta_ahorro_mensual: Decimal = Decimal('0.00')
    alert_meta_ahorro_enabled: bool = False
    alert_balance_critico_enabled: bool = True
    
    # MICRO-GASTOS
    alert_micro_gastos_enabled: bool = True
    alert_micro_gastos_cantidad: int = 10
    alert_micro_gastos_monto_max: Decimal = Decimal('10000.00')
    alert_gastos_hormiga_enabled: bool = True
    alert_gastos_hormiga_monto_dia: Decimal = Decimal('50000.00')
    
    # PREDICTIVAS
    alert_proyeccion_sobregasto_enabled: bool = True
    alert_comparacion_periodo_enabled: bool = True
    alert_dia_mes_critico_enabled: bool = True
    alert_dia_mes_critico_porcentaje: int = 70
    
    # INCONSISTENCIAS
    alert_egreso_sin_concepto_enabled: bool = False
    alert_egreso_sin_concepto_cantidad: int = 5
    alert_ingreso_inusual_enabled: bool = True
    alert_ingreso_inusual_multiplicador: Decimal = Decimal('2.50')

DEFAULT_PREFS = PrefsDTO()
