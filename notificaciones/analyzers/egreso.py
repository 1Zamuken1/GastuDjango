from notificaciones.analyzers.base import BaseAnalyzer
from notificaciones.checks.egreso_checks import (
    CheckUmbralMensual, CheckDeficit, CheckEgresoGrande, 
    CheckGastoIncremental, CheckPatronInusualEgresos, 
    CheckConcentracionGastos, CheckVelocidadGasto, 
    CheckEgresosAgrupados, CheckBalanceCritico, 
    CheckMicroGastos, CheckGastosHormiga, 
    CheckProyeccionSobregasto, CheckComparacionPeriodoEgresos, 
    CheckDiaMesCritico, CheckEgresoSinConcepto
)

class EgresoAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__([
            CheckUmbralMensual,
            CheckDeficit,
            CheckEgresoGrande,
            CheckGastoIncremental,
            CheckPatronInusualEgresos,
            CheckConcentracionGastos,
            CheckVelocidadGasto,
            CheckEgresosAgrupados,
            CheckBalanceCritico,
            CheckMicroGastos,
            CheckGastosHormiga,
            CheckProyeccionSobregasto,
            CheckComparacionPeriodoEgresos,
            CheckDiaMesCritico,
            CheckEgresoSinConcepto
        ])
