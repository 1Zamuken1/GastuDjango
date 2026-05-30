import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificacionesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        print(f"[WS] Intento de conexión de: {self.user}")
        if self.user.is_anonymous:
            await self.close()
        else:
            self.group_name = f"notificaciones_{self.user.id}"
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
            print(f"[WS] Conectado exitosamente al grupo: {self.group_name}")

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def notificacion_mensaje(self, event):
        print(f"[WS] Recibiendo evento notificacion_mensaje para enviar a cliente: {event['data']}")
        # Enviar mensaje al WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notificacion',
            'data': event['data']
        }))
