from django.core.cache import cache
from django.conf import settings
from .models import PreferenciasAlertas
from .defaults import PrefsDTO, DEFAULT_PREFS

class PreferenciasService:
    CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

    @classmethod
    def _get_cache_key(cls, usuario_id):
        return f"prefs_alertas_{usuario_id}"

    @classmethod
    def obtener(cls, usuario) -> PrefsDTO:
        """
        Obtiene las preferencias del usuario (usando cache).
        Si no existen en DB, retorna defaults sin guardarlos en DB 
        (se guardaran la primera vez que el usuario edite su perfil).
        """
        if not usuario or not usuario.is_authenticated:
            return DEFAULT_PREFS

        cache_key = cls._get_cache_key(usuario.id)
        prefs_data = cache.get(cache_key)

        if prefs_data is not None:
            return PrefsDTO(**prefs_data)

        # Buscar en DB
        try:
            prefs_obj = PreferenciasAlertas.objects.get(usuario=usuario)
            dto = cls._to_dto(prefs_obj)
            cls._set_cache(usuario.id, dto)
            return dto
        except PreferenciasAlertas.DoesNotExist:
            return DEFAULT_PREFS

    @classmethod
    def _to_dto(cls, prefs_obj: PreferenciasAlertas) -> PrefsDTO:
        """Convierte una instancia de modelo a PrefsDTO."""
        return PrefsDTO(
            umbral_advertencia_porcentaje=prefs_obj.umbral_advertencia_porcentaje,
            egreso_grande_porcentaje=prefs_obj.egreso_grande_porcentaje,
            alerta_egreso_grande_activa=prefs_obj.alerta_egreso_grande_activa,
            
            alert_gasto_incremental_enabled=prefs_obj.alert_gasto_incremental_enabled,
            alert_gasto_incremental_porcentaje=prefs_obj.alert_gasto_incremental_porcentaje,
            alert_gasto_incremental_meses=prefs_obj.alert_gasto_incremental_meses,
            alert_reduccion_ingresos_enabled=prefs_obj.alert_reduccion_ingresos_enabled,
            alert_reduccion_ingresos_porcentaje=prefs_obj.alert_reduccion_ingresos_porcentaje,
            alert_patron_inusual_enabled=prefs_obj.alert_patron_inusual_enabled,
            
            alert_concentracion_gastos_enabled=prefs_obj.alert_concentracion_gastos_enabled,
            alert_concentracion_gastos_porcentaje=prefs_obj.alert_concentracion_gastos_porcentaje,
            alert_concepto_sin_uso_enabled=prefs_obj.alert_concepto_sin_uso_enabled,
            alert_concepto_sin_uso_dias=prefs_obj.alert_concepto_sin_uso_dias,
            
            alert_velocidad_gasto_enabled=prefs_obj.alert_velocidad_gasto_enabled,
            alert_inactividad_ingresos_enabled=prefs_obj.alert_inactividad_ingresos_enabled,
            alert_inactividad_dias=prefs_obj.alert_inactividad_dias,
            alert_egresos_agrupados_enabled=prefs_obj.alert_egresos_agrupados_enabled,
            alert_egresos_agrupados_cantidad=prefs_obj.alert_egresos_agrupados_cantidad,
            alert_egresos_agrupados_horas=prefs_obj.alert_egresos_agrupados_horas,
            
            meta_ahorro_mensual=prefs_obj.meta_ahorro_mensual,
            alert_meta_ahorro_enabled=prefs_obj.alert_meta_ahorro_enabled,
            alert_balance_critico_enabled=prefs_obj.alert_balance_critico_enabled,
            
            alert_micro_gastos_enabled=prefs_obj.alert_micro_gastos_enabled,
            alert_micro_gastos_cantidad=prefs_obj.alert_micro_gastos_cantidad,
            alert_micro_gastos_monto_max=prefs_obj.alert_micro_gastos_monto_max,
            alert_gastos_hormiga_enabled=prefs_obj.alert_gastos_hormiga_enabled,
            alert_gastos_hormiga_monto_dia=prefs_obj.alert_gastos_hormiga_monto_dia,
            
            alert_proyeccion_sobregasto_enabled=prefs_obj.alert_proyeccion_sobregasto_enabled,
            alert_comparacion_periodo_enabled=prefs_obj.alert_comparacion_periodo_enabled,
            alert_dia_mes_critico_enabled=prefs_obj.alert_dia_mes_critico_enabled,
            alert_dia_mes_critico_porcentaje=prefs_obj.alert_dia_mes_critico_porcentaje,
            
            alert_egreso_sin_concepto_enabled=prefs_obj.alert_egreso_sin_concepto_enabled,
            alert_egreso_sin_concepto_cantidad=prefs_obj.alert_egreso_sin_concepto_cantidad,
            alert_ingreso_inusual_enabled=prefs_obj.alert_ingreso_inusual_enabled,
            alert_ingreso_inusual_multiplicador=prefs_obj.alert_ingreso_inusual_multiplicador,
        )

    @classmethod
    def _set_cache(cls, usuario_id, dto: PrefsDTO):
        """Guarda en cache como diccionario."""
        cache.set(cls._get_cache_key(usuario_id), dto.__dict__, cls.CACHE_TIMEOUT)

    @classmethod
    def invalidar_cache(cls, usuario_id):
        """Elimina las preferencias cacheadas (ej: tras actualizarlas)."""
        cache.delete(cls._get_cache_key(usuario_id))
