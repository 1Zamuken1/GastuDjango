import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

class NotificacionesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        logger.debug(f"Intento de conexión WS de: {self.user}")
        if self.user.is_anonymous:
            await self.close()
        else:
            self.group_name = f"notificaciones_{self.user.id}"
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
            logger.debug(f"Conectado exitosamente al grupo: {self.group_name}")

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def notificacion_mensaje(self, event):
        logger.debug(f"Enviando notificación a cliente: {event['data'].get('tipo', '')}")
        # Enviar mensaje al WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notificacion',
            'data': event['data']
        }))
