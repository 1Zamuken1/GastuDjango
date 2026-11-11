"""API del chat con el agente GASTU: mensajes, historial y confirmacion de acciones."""

import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from . import acciones
from .groq_client import GroqError, preguntar_a_groq
from .herramientas import EjecutorHerramientas
from .models import AccionPendiente, MensajeChat
from .prompt_builder import construir_prompt
from .recolector import RecolectorDatos
from .servicios_bloques import detectar_y_ensamblar_bloques

logger = logging.getLogger(__name__)

MAX_HISTORIAL_CONTEXTO = 4
MAX_HISTORIAL_RESPUESTA = 50
MAX_LARGO_MENSAJE = 1000
MSG_CUPO_DIARIO = "Llegaste al límite de consultas de hoy. Vuelve mañana para seguir conversando con Gastu."


def _clave_cupo(usuario_id) -> str:
    return f"agente_mensajes:{usuario_id}:{timezone.localdate().isoformat()}"


def consumir_cupo_diario(usuario) -> bool:
    """Descuenta un mensaje del cupo diario del usuario. False si ya no le quedan."""
    clave = _clave_cupo(usuario.pk)
    cache.add(clave, 0, timeout=60 * 60 * 26)
    try:
        usados = cache.incr(clave)
    except ValueError:
        cache.set(clave, 1, timeout=60 * 60 * 26)
        usados = 1
    return usados <= getattr(settings, "AGENTE_MAX_MENSAJES_DIA", 100)


def _con_tarjetas(bloques, respuesta, tarjetas):
    """Agrega las tarjetas (confirmaciones, descargas) que prepararon las herramientas."""
    if not tarjetas:
        return bloques
    base = list(bloques) if bloques else [{"tipo": "texto", "texto": respuesta}]
    return base + tarjetas


def _estado_tarjetas(usuario, mensajes):
    """Marca en el historial si cada confirmacion sigue pendiente, para no ofrecer botones muertos."""
    tokens = [
        b.get("token") for m in mensajes for b in (m["bloques"] or [])
        if isinstance(b, dict) and b.get("tipo") == "confirmacion"
    ]
    if not tokens:
        return
    estados = {
        a.token: ("VENCIDA" if a.estado == AccionPendiente.Estado.PENDIENTE and a.vencida else a.estado)
        for a in AccionPendiente.objects.filter(usuario=usuario, token__in=tokens)
    }
    for m in mensajes:
        for b in m["bloques"] or []:
            if isinstance(b, dict) and b.get("tipo") == "confirmacion":
                b["estado"] = estados.get(b.get("token"), "VENCIDA")


@method_decorator(login_required, name="dispatch")
@method_decorator(ratelimit(key="user", rate="15/m", method="POST", block=False), name="post")
@method_decorator(ratelimit(key="ip", rate="30/m", method="POST", block=False), name="post")
class ChatView(View):
    """API del chat con el agente GASTU."""

    def get(self, request, *args, **kwargs):
        """Ultimos mensajes del historial del usuario, con sus bloques estructurados."""
        mensajes = list(
            MensajeChat.objects.filter(usuario=request.user)
            .order_by("-creado_en")
            .values("rol", "contenido", "bloques", "animo", "procedencia", "creado_en")[:MAX_HISTORIAL_RESPUESTA]
        )
        mensajes.reverse()
        _estado_tarjetas(request.user, mensajes)
        return JsonResponse({
            "ok": True,
            "mensajes": [
                {
                    "rol": m["rol"],
                    "contenido": m["contenido"],
                    "bloques": m["bloques"],
                    "animo": m["animo"],
                    "procedencia": m["procedencia"],
                    "hora": timezone.localtime(m["creado_en"]).strftime("%H:%M"),
                }
                for m in mensajes
            ],
        })

    def post(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return JsonResponse({
                "ok": False,
                "error": "Has enviado demasiados mensajes. Espera un momento antes de continuar.",
            }, status=429)

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({"ok": False, "error": "Body debe ser JSON válido."}, status=400)
        if not isinstance(body, dict):
            return JsonResponse({"ok": False, "error": "Body debe ser JSON válido."}, status=400)

        pregunta = str(body.get("mensaje", "") or "").strip()
        if not pregunta:
            return JsonResponse({"ok": False, "error": "El campo 'mensaje' no puede estar vacío."}, status=400)
        if len(pregunta) > MAX_LARGO_MENSAJE:
            return JsonResponse({"ok": False, "error": "Mensaje demasiado largo (máximo 1000 caracteres)."}, status=400)

        if not consumir_cupo_diario(request.user):
            return JsonResponse({"ok": False, "error": MSG_CUPO_DIARIO}, status=429)

        try:
            datos = RecolectorDatos(request.user).recolectar_todo()
            # El historial se lee ANTES de guardar la pregunta: si no, el modelo la recibe dos veces.
            historial_previo = list(
                MensajeChat.objects.filter(usuario=request.user).order_by("-creado_en")[:MAX_HISTORIAL_CONTEXTO]
            )
            historial_previo.reverse()
            mensajes = construir_prompt(datos, pregunta, historial_previo)
        except Exception:
            logger.exception("[GASTU] Error preparando la consulta usuario %s", request.user.pk)
            return JsonResponse({"ok": False, "error": "Error al obtener tus datos financieros."}, status=500)

        msg_usuario = MensajeChat.objects.create(usuario=request.user, rol="user", contenido=pregunta)
        ejecutor = EjecutorHerramientas(request.user)

        try:
            respuesta = preguntar_a_groq(mensajes, ejecutor.ejecutar)
            if not respuesta and ejecutor.tarjetas:
                respuesta = "Te dejé lista la acción. Revísala y confirma si está bien."
            bloques, animo, procedencia = detectar_y_ensamblar_bloques(request.user, pregunta, respuesta_llm=respuesta)
            bloques = _con_tarjetas(bloques, respuesta, ejecutor.tarjetas)
            MensajeChat.objects.create(
                usuario=request.user, rol="bot", contenido=respuesta or "",
                bloques=bloques or None, animo=animo, procedencia=procedencia,
            )
            datos_respuesta = {"ok": True, "respuesta": respuesta}
            if bloques:
                datos_respuesta.update({"bloques": bloques, "animo": animo, "procedencia": procedencia})
            return JsonResponse(datos_respuesta)

        except Exception as exc:
            es_groq = isinstance(exc, GroqError)
            if es_groq:
                logger.warning("[GASTU] GroqError usuario %s: %s", request.user.pk, exc)
            else:
                logger.exception("[GASTU] Error inesperado en el chat usuario %s", request.user.pk)

            # Respaldo determinista si la consulta es sobre presupuestos o movimientos.
            bloques_fb, animo_fb, proc_fb = detectar_y_ensamblar_bloques(request.user, pregunta, respuesta_llm=None)
            if bloques_fb:
                txt_resp = bloques_fb[0]["texto"]
                MensajeChat.objects.create(
                    usuario=request.user, rol="bot", contenido=txt_resp,
                    bloques=bloques_fb, animo=animo_fb, procedencia=proc_fb,
                )
                return JsonResponse({
                    "ok": True, "respuesta": txt_resp,
                    "bloques": bloques_fb, "animo": animo_fb, "procedencia": proc_fb,
                })

            msg_usuario.delete()
            # str(GroqError) ya es un mensaje para el usuario; el detalle del proveedor va solo al log.
            mensaje = str(exc) if es_groq else "Error al conectar con el asistente."
            return JsonResponse({"ok": False, "error": mensaje}, status=503 if es_groq else 500)


@method_decorator(login_required, name="dispatch")
class LimpiarChatView(View):

    def post(self, request, *args, **kwargs):
        """Borra todo el historial del usuario."""
        eliminados, _ = MensajeChat.objects.filter(usuario=request.user).delete()
        return JsonResponse({"ok": True, "eliminados": eliminados})


@login_required
@require_POST
@ratelimit(key="user", rate="30/m", method="POST", block=False)
def resolver_accion_view(request, token, decision):
    """Confirma o cancela una accion preparada por el agente (solo del propio usuario)."""
    if getattr(request, "limited", False):
        return JsonResponse({"ok": False, "error": "Demasiadas solicitudes. Espera un momento."}, status=429)
    try:
        if decision == "confirmar":
            mensaje = acciones.confirmar_accion(request.user, token)
            estado = AccionPendiente.Estado.CONFIRMADA
        elif decision == "cancelar":
            mensaje = acciones.cancelar_accion(request.user, token)
            estado = AccionPendiente.Estado.CANCELADA
        else:
            return JsonResponse({"ok": False, "error": "Decisión inválida."}, status=400)
    except acciones.ErrorAccion as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    except Exception:
        logger.exception("[GASTU] Error resolviendo accion usuario %s", request.user.pk)
        return JsonResponse({"ok": False, "error": "No se pudo completar la acción."}, status=500)
    return JsonResponse({"ok": True, "estado": estado, "mensaje": mensaje})


chat_view = ChatView.as_view()
limpiar_view = LimpiarChatView.as_view()
