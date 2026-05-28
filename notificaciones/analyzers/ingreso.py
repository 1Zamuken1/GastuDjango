from notificaciones.analyzers.base import BaseAnalyzer
from notificaciones.checks.ingreso_checks import (
    CheckReduccionIngresos, CheckInactividadIngresos, 
    CheckIngresoInusual, CheckConceptoSinUso
)

class IngresoAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__([
            CheckReduccionIngresos,
            CheckInactividadIngresos,
            CheckIngresoInusual,
            CheckConceptoSinUso
        ])
