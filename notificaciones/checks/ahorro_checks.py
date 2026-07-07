from decimal import Decimal
from django.utils import timezone
from notificaciones.models import Notificacion
from ahorros.models import AporteAhorro

class AhorroAnalyzer:
    """
    Analiza si existen cuotas de ahorro próximas a vencer en la ventana de pago
    configurada por el usuario.
    """
    def __init__(self, usuario, preferencias):
        self.usuario = usuario
        self.prefs = preferencias

    def analizar(self):
        alertas = []
        
        if not self.prefs.alert_recordatorio_ahorro_enabled:
            return alertas

        hoy = timezone.now().date()
        dias_ventana = self.prefs.alert_recordatorio_ahorro_dias
        limite_ventana = hoy + timezone.timedelta(days=dias_ventana)

        # Buscamos aportes pendientes del usuario que estén en la ventana de pago
        aportes_pendientes = AporteAhorro.objects.filter(
            ahorro__usuario=self.usuario,
            estado_ap=AporteAhorro.EstadoAp.PENDIENTE.value,
            fecha_limite__gte=hoy,
            fecha_limite__lte=limite_ventana
        ).select_related('ahorro', 'ahorro__categoria')

        for aporte in aportes_pendientes:
            dias_restantes = (aporte.fecha_limite - hoy).days
            if dias_restantes == 0:
                mensaje = "vence hoy"
            elif dias_restantes == 1:
                mensaje = "vence mañana"
            else:
                mensaje = f"vence en {dias_restantes} días"

            nombre_ahorro = aporte.ahorro.descripcion or aporte.ahorro.categoria.nombre

            alertas.append({
                'tipo': Notificacion.Tipo.RECORDATORIO_CUOTA_AHORRO,
                'titulo': 'Recordatorio de Ahorro',
                'descripcion': f'La cuota de ${aporte.aporte_asignado} para el ahorro "{nombre_ahorro}" {mensaje}.',
                'referencia_id': str(aporte.id),
                'referencia_tipo': 'APORTE_AHORRO'
            })
            
        return alertas
