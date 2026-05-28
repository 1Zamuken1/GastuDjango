from dataclasses import dataclass
from django.utils import timezone
from notificaciones.preferencias.defaults import PrefsDTO

@dataclass
class CheckContext:
    """
    Contexto compartido para los analyzers.
    Evita que cada analyzer vuelva a consultar la DB por los mismos datos basicos.
    """
    usuario: any
    preferencias: PrefsDTO
    now: timezone.datetime
    
    # Datos en cache lazy
    _inicio_mes: timezone.datetime = None
    _total_egresos_mes: float = None
    _total_ingresos_mes: float = None

    @property
    def inicio_mes(self):
        if self._inicio_mes is None:
            self._inicio_mes = self.now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return self._inicio_mes

    @property
    def dias_del_mes(self):
        import calendar
        return calendar.monthrange(self.now.year, self.now.month)[1]

    @property
    def total_egresos_mes(self):
        if self._total_egresos_mes is None:
            from notificaciones.checks.query_helpers import total_en_rango
            self._total_egresos_mes = total_en_rango(self.usuario, 'EGRESO', self.inicio_mes, self.now)
        return self._total_egresos_mes

    @property
    def total_ingresos_mes(self):
        if self._total_ingresos_mes is None:
            from notificaciones.checks.query_helpers import total_en_rango
            self._total_ingresos_mes = total_en_rango(self.usuario, 'INGRESO', self.inicio_mes, self.now)
        return self._total_ingresos_mes
