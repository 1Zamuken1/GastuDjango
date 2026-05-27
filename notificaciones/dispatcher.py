import concurrent.futures
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from notificaciones.preferencias.service import PreferenciasService
from notificaciones.checks.context import CheckContext
from notificaciones.analyzers.egreso import EgresoAnalyzer
from notificaciones.analyzers.ingreso import IngresoAnalyzer
from notificaciones.repository import NotificacionRepository

class NotificationDispatcher:
    _executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    @classmethod
    def dispatch(cls, usuario, movimiento):
        """Envía la tarea de análisis al pool de hilos para no bloquear."""
        cls._executor.submit(cls._analyze_and_notify, usuario, movimiento)

    @classmethod
    def _analyze_and_notify(cls, usuario, movimiento):
        try:
            prefs = PreferenciasService.obtener(usuario)
            ctx = CheckContext(usuario=usuario, preferencias=prefs, now=timezone.now())

            analyzer = EgresoAnalyzer() if movimiento.tipo == 'EGRESO' else IngresoAnalyzer()
            alertas_data = analyzer.analyze(ctx, movimiento)

            if not alertas_data:
                return

            nuevas_notificaciones = []
            for alerta in alertas_data:
                # El repository maneja anti-duplicados y persistencia
                notif = NotificacionRepository.guardar_si_no_existe(usuario, alerta)
                if notif:
                    nuevas_notificaciones.append(notif)

            if nuevas_notificaciones:
                cls._push_to_websocket(usuario.id, nuevas_notificaciones)

        except Exception as e:
            print(f"[notificaciones] Error en background task para {usuario}: {e}")

    @classmethod
    def _push_to_websocket(cls, usuario_id, notificaciones):
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        group_name = f"notificaciones_{usuario_id}"
        
        for notif in notificaciones:
            data = {
                'id': notif.id,
                'tipo': notif.tipo,
                'titulo': notif.titulo,
                'descripcion': notif.descripcion,
                'fecha_creacion': notif.fecha_creacion.isoformat(),
                'modulo': notif.modulo,
            }
            try:
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'notificacion_mensaje',
                        'data': data
                    }
                )
            except Exception as e:
                print(f"[notificaciones] Error enviando a websocket {group_name}: {e}")
