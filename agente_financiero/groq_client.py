"""
Cliente HTTP para GroqCloud con tool calling en varias vueltas.

- Modelo principal y de respaldo configurables (GROQ_MODEL, GROQ_MODEL_RESPALDO):
  si el principal deja de existir (404) o el servicio falla (5xx), se reintenta
  la misma conversacion con el respaldo.
- La ultima vuelta se hace sin herramientas, para que el modelo siempre termine
  con una respuesta en texto aunque haya seguido pidiendo tools.
- Tope de llamadas a herramientas por vuelta y de vueltas por pregunta.
- GroqError lleva un mensaje apto para el usuario; el detalle del proveedor
  solo va al log.
"""

import json
import logging
import re
import time

import requests
from django.conf import settings

from .tools_schema import TOOLS

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_TOOL_CALLS_POR_VUELTA = 5
MAX_ARGUMENTOS_BYTES = 4000


class GroqError(Exception):
    """Error de conexion o respuesta con GroqCloud. str(error) es apto para el usuario."""


class _ModeloNoDisponible(Exception):
    """El modelo no existe, fallo o agoto su cuota: vale la pena probar el de respaldo."""

    def __init__(self, motivo, mensaje_usuario="El asistente no está disponible en este momento. Intenta más tarde."):
        super().__init__(motivo)
        self.mensaje_usuario = mensaje_usuario


def modelos_configurados() -> list:
    """Modelo principal y respaldos en orden. GROQ_MODEL_RESPALDO admite una lista separada por comas."""
    principal = getattr(settings, "GROQ_MODEL", "") or "openai/gpt-oss-120b"
    respaldos = [m.strip() for m in str(getattr(settings, "GROQ_MODEL_RESPALDO", "") or "").split(",")]
    return [m for m in dict.fromkeys([principal, *respaldos]) if m]


# Tope de max_tokens por familia: en el plan gratuito algunos modelos limitan los
# tokens de salida por minuto (qwen3.8: 1.000) y rechazan cualquier peticion que
# reserve mas, aunque la respuesta real sea corta.
TOPE_SALIDA = {"qwen/": 900}


def _opciones_modelo(modelo: str, max_tokens: int) -> dict:
    """Parametros propios de cada familia de modelos."""
    tope = next((v for prefijo, v in TOPE_SALIDA.items() if modelo.startswith(prefijo)), max_tokens)
    opciones = {"max_tokens": min(max_tokens, tope)}
    if modelo.startswith("openai/gpt-oss"):
        # Razona antes de responder: esfuerzo bajo para no gastar tokens ni latencia.
        opciones["reasoning_effort"] = getattr(settings, "GROQ_REASONING_EFFORT", "low")
    return opciones


def _mensaje_para_historial(mensaje: dict) -> dict:
    """Copia del mensaje del asistente sin campos que otro modelo no acepta (reasoning)."""
    return {k: v for k, v in mensaje.items() if k in ("role", "content", "tool_calls")}


def _argumentos(tool_call) -> dict:
    crudo = (tool_call.get("function") or {}).get("arguments") or "{}"
    if len(crudo) > MAX_ARGUMENTOS_BYTES:
        return {"__invalido__": True}
    try:
        valor = json.loads(crudo)
    except (json.JSONDecodeError, TypeError):
        return {"__invalido__": True}
    return valor if isinstance(valor, dict) else {"__invalido__": True}


def _conversar(modelo, mensajes, ejecutar_herramienta_fn, max_tokens, max_vueltas) -> str:
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    mensajes_actuales = list(mensajes)

    for vuelta in range(max_vueltas):
        es_ultima = vuelta == max_vueltas - 1
        payload = {
            "model": modelo,
            "messages": mensajes_actuales,
            "temperature": 0.3,
            "stream": False,
            **_opciones_modelo(modelo, max_tokens),
        }
        if not es_ultima:
            payload["tools"] = TOOLS
            payload["tool_choice"] = "auto"

        data = _hacer_request(headers, payload).json()
        try:
            choice = data["choices"][0]
            mensaje = choice["message"]
        except (KeyError, IndexError, TypeError):
            logger.error("[GASTU] Respuesta de Groq sin choices: %s", str(data)[:300])
            raise GroqError("El asistente devolvió una respuesta inválida. Intenta de nuevo.")

        tool_calls = mensaje.get("tool_calls") or []
        if es_ultima or not tool_calls:
            return (mensaje.get("content") or "").strip()

        mensajes_actuales.append(_mensaje_para_historial(mensaje))
        for i, tool_call in enumerate(tool_calls):
            nombre = (tool_call.get("function") or {}).get("name", "")
            if i >= MAX_TOOL_CALLS_POR_VUELTA:
                resultado = json.dumps({"error": "Demasiadas herramientas en una sola vuelta; usa menos."})
            else:
                argumentos = _argumentos(tool_call)
                if argumentos.get("__invalido__"):
                    resultado = json.dumps({"error": "Los argumentos no son un objeto JSON válido."})
                else:
                    resultado = ejecutar_herramienta_fn(nombre, argumentos)
            mensajes_actuales.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id", ""),
                "content": resultado,
            })

    return ""


def preguntar_a_groq(mensajes: list, ejecutar_herramienta_fn, max_tokens: int = 1200, max_vueltas: int = 4) -> str:
    """
    Envia la conversacion a Groq, resuelve las tools en bucle y retorna el texto final.

    max_tokens cuenta contra el limite de tokens por minuto aunque no se usen (Groq
    reserva prompt + max_tokens), asi que se deja justo para una respuesta del chat.
    """
    if not getattr(settings, "GROQ_API_KEY", None):
        logger.error("[GASTU] GROQ_API_KEY no esta configurada")
        raise GroqError("El asistente no está disponible en este momento.")

    modelos = modelos_configurados()
    for i, modelo in enumerate(modelos):
        try:
            return _conversar(modelo, mensajes, ejecutar_herramienta_fn, max_tokens, max_vueltas)
        except _ModeloNoDisponible as exc:
            logger.warning("[GASTU] Modelo %s no disponible (%s)", modelo, exc)
            if i == len(modelos) - 1:
                raise GroqError(exc.mensaje_usuario)
    raise GroqError("El asistente no está disponible en este momento.")


def _detalle_error(response) -> str:
    try:
        return response.json().get("error", {}).get("message", "") or response.text
    except Exception:
        return response.text


def _hacer_request(headers: dict, payload: dict, max_intentos: int = 2) -> requests.Response:
    """POST a GroqCloud con un reintento ante rate limit (429)."""
    for intento in range(1, max_intentos + 1):
        try:
            response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=40)
        except requests.exceptions.Timeout:
            raise GroqError("El asistente tardó demasiado en responder. Intenta de nuevo.")
        except requests.exceptions.RequestException as exc:
            logger.error("[GASTU] Error de conexion con Groq: %s", exc)
            raise _ModeloNoDisponible("conexion")

        if response.status_code == 200:
            return response

        detalle = _detalle_error(response)
        logger.warning("[GASTU] Groq HTTP %s modelo=%s: %s", response.status_code, payload.get("model"), detalle[:300])

        if response.status_code == 429:
            match = re.search(r'try again in ([\d\.]+)s', detalle)
            espera = float(match.group(1)) if match else 5.0
            if intento < max_intentos and espera <= 8:
                time.sleep(espera + 0.5)
                continue
            # Cada modelo tiene su propia cuota en Groq: se prueba el de respaldo.
            segundos = f" unos {int(espera) + 1} segundos" if match else " un momento"
            raise _ModeloNoDisponible(
                "HTTP 429",
                f"Límite de consultas alcanzado temporalmente. Espera{segundos} y vuelve a preguntar.",
            )

        if response.status_code in (404, 410) or response.status_code >= 500:
            raise _ModeloNoDisponible(f"HTTP {response.status_code}")
        if response.status_code == 400 and "model" in detalle.lower() and "decommission" in detalle.lower():
            raise _ModeloNoDisponible("modelo retirado")

        raise GroqError("El asistente no pudo procesar la consulta. Intenta reformularla.")

    raise GroqError("El asistente no está disponible en este momento.")
