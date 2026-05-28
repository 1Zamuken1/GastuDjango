from django.core.management.base import BaseCommand
from usuarios.models import Usuario
from notificaciones.preferencias.models import PreferenciasAlertas
from notificaciones.checks.ahorro_checks import AhorroAnalyzer
from notificaciones.repository import NotificacionRepository
from notificaciones.dispatcher import NotificationDispatcher

class Command(BaseCommand):
    help = 'Procesa los recordatorios diarios de ahorros para todos los usuarios'

    def handle(self, *args, **options):
        usuarios = Usuario.objects.all()
        total_alertas = 0
        
        self.stdout.write("Iniciando procesamiento de recordatorios de ahorro...")

        for usuario in usuarios:
            try:
                prefs = usuario.prefs_alertas
            except PreferenciasAlertas.DoesNotExist:
                continue

            if not prefs.alert_recordatorio_ahorro_enabled:
                continue

            analyzer = AhorroAnalyzer(usuario, prefs)
            alertas = analyzer.analizar()

            nuevas_notificaciones = []
            for alerta in alertas:
                notif = NotificacionRepository.guardar_si_no_existe(usuario, alerta)
                if notif:
                    nuevas_notificaciones.append(notif)
                    total_alertas += 1

            if nuevas_notificaciones:
                # Si hay nuevas notificaciones, intentamos enviarlas por WebSocket
                # Esto es seguro porque si falla Redis, solo lanza un warning en consola.
                NotificationDispatcher._push_to_websocket(usuario.id, nuevas_notificaciones)

        # Esperamos a que los hilos terminen antes de matar el proceso
        NotificationDispatcher._executor.shutdown(wait=True)
        self.stdout.write(self.style.SUCCESS(f"Procesamiento completado. Se generaron {total_alertas} recordatorios nuevos."))
