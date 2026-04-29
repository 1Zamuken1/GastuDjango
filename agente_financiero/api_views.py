"""
agente_financiero/api_views.py

Endpoints del agente financiero:
  GET  /api/agente/chat/    → retorna el historial del usuario
  POST /api/agente/chat/    → envía un mensaje, guarda pregunta y respuesta
  POST /api/agente/limpiar/ → borra el historial del usuario
"""

import json
import logging

from django.http import JsonResponse
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from .recolector import RecolectorDatos
from .prompt_builder import construir_prompt
from .groq_client import preguntar_a_groq, GroqError
from .herramientas import EjecutorHerramientas
from .models import MensajeChat

logger = logging.getLogger(__name__)

MAX_HISTORIAL_CONTEXTO = 10  # Cuántos mensajes previos se pasan al LLM


@method_decorator(login_required, name="dispatch")
class ChatView(View):

    def get(self, request, *args, **kwargs):
        """Retorna el historial completo del usuario."""
        mensajes = MensajeChat.objects.filter(usuario=request.user).values(
            "rol", "contenido", "creado_en"
        )

        return JsonResponse({
            "ok": True,
            "mensajes": [
                {
                    "rol": m["rol"],
                    "contenido": m["contenido"],
                    "hora": m["creado_en"].strftime("%H:%M"),
                }
                for m in mensajes
            ],
        })

    def post(self, request, *args, **kwargs):
        """Recibe un mensaje, llama al agente y guarda ambos en BD."""
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"ok": False, "error": "Body debe ser JSON válido."}, status=400)

        pregunta = body.get("mensaje", "").strip()
        if not pregunta:
            return JsonResponse({"ok": False, "error": "El campo 'mensaje' no puede estar vacío."}, status=400)
        if len(pregunta) > 1000:
            return JsonResponse({"ok": False, "error": "Mensaje demasiado largo (máximo 1000 caracteres)."}, status=400)

        # Recolectar datos financieros del usuario
        try:
            datos = RecolectorDatos(request.user).recolectar_todo()
        except Exception as e:
            logger.error(f"[GASTU] Error recolectando datos usuario {request.user.id}: {e}")
            return JsonResponse({"ok": False, "error": "Error al obtener tus datos financieros."}, status=500)

        # Construir prompt con los últimos N mensajes como contexto
        try:
            historial_previo = list(
                MensajeChat.objects.filter(usuario=request.user)
                .order_by("-creado_en")[:MAX_HISTORIAL_CONTEXTO]
            )
            historial_previo.reverse()  # Cronológico
            mensajes = construir_prompt(datos, pregunta, historial_previo)
        except Exception as e:
            logger.error(f"[GASTU] Error construyendo prompt usuario {request.user.id}: {e}")
            return JsonResponse({"ok": False, "error": "Error interno al preparar la consulta."}, status=500)

        # Llamar a Groq con tool calling
        ejecutor = EjecutorHerramientas(request.user)
        try:
            respuesta = preguntar_a_groq(mensajes, ejecutor.ejecutar)
        except GroqError as e:
            logger.error(f"[GASTU] GroqError usuario {request.user.id}: {e}")
            return JsonResponse({"ok": False, "error": str(e)}, status=503)
        except Exception as e:
            logger.error(f"[GASTU] Error inesperado Groq usuario {request.user.id}: {e}")
            return JsonResponse({"ok": False, "error": "Error al conectar con el asistente."}, status=500)

        # Guardar ambos mensajes en BD
        MensajeChat.objects.create(usuario=request.user, rol="user", contenido=pregunta)
        MensajeChat.objects.create(usuario=request.user, rol="bot", contenido=respuesta)

        return JsonResponse({"ok": True, "respuesta": respuesta})


@method_decorator(login_required, name="dispatch")
class LimpiarChatView(View):

    def post(self, request, *args, **kwargs):
        """Borra todo el historial del usuario."""
        eliminados, _ = MensajeChat.objects.filter(usuario=request.user).delete()
        return JsonResponse({"ok": True, "eliminados": eliminados})


chat_view    = ChatView.as_view()
limpiar_view = LimpiarChatView.as_view()