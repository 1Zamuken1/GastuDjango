"""Cliente HTTP para GroqCloud con soporte de tool calling."""

import json
import requests
from django.conf import settings

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqError(Exception):
    """Error de conexión o respuesta con GroqCloud."""
    pass


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "obtener_movimientos",
            "description": (
                "Consulta los movimientos del usuario aplicando filtros opcionales. "
                "Úsala cuando el usuario pregunte por gastos, ingresos, historial, "
                "o quiera saber cuánto gastó/ingresó en un período o categoría."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo": {
                        "type": "string",
                        "enum": ["INGRESO", "EGRESO", "TODOS"],
                        "description": "Filtrar por tipo de movimiento. Usa TODOS si no se especifica.",
                    },
                    "mes": {
                        "type": "integer",
                        "description": "Número de mes (1-12). Omitir si no se especifica.",
                    },
                    "anio": {
                        "type": "integer",
                        "description": "Año de 4 dígitos. Omitir si no se especifica.",
                    },
                    "categoria": {
                        "type": "string",
                        "description": "Nombre parcial de la categoría a filtrar (búsqueda por contenido).",
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Cantidad máxima de registros a retornar. Default 20, máximo 100.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_resumen_periodo",
            "description": (
                "Calcula ingresos totales, egresos totales y balance de un período específico. "
                "Úsala cuando el usuario pregunte por totales, balances o comparaciones entre meses."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "mes": {
                        "type": "integer",
                        "description": "Número de mes (1-12).",
                    },
                    "anio": {
                        "type": "integer",
                        "description": "Año de 4 dígitos.",
                    },
                },
                "required": ["mes", "anio"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_gastos_por_categoria",
            "description": (
                "Agrupa y suma los egresos por categoría en un período dado. "
                "Úsala cuando el usuario pregunte en qué gasta más, distribución de gastos, "
                "o quiera ver un desglose por categoría."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "mes": {
                        "type": "integer",
                        "description": "Número de mes (1-12). Omitir para todos los meses del año.",
                    },
                    "anio": {
                        "type": "integer",
                        "description": "Año de 4 dígitos.",
                    },
                },
                "required": ["anio"],
            },
        },
    },
]

def preguntar_a_groq(mensajes: list, ejecutar_herramienta_fn, max_tokens: int = 1024) -> str:
    """Envía mensajes a Groq, maneja tool calls y retorna la respuesta final del asistente."""
   
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        raise GroqError(
            "GROQ_API_KEY no está configurada en settings.py. "
            "Agrega GROQ_API_KEY=gsk_... a tu archivo .env"
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # primera llamada valida si necesita las herramientas o no
    payload = {
        "model": GROQ_MODEL,
        "messages": mensajes,
        "tools": TOOLS,
        "tool_choice": "auto",
        "max_tokens": max_tokens,
        "temperature": 0.4,
        "top_p": 0.9,
        "stream": False,
    }

    response = _hacer_request(headers, payload)
    data = response.json()
    choice = data["choices"][0]
    mensaje_asistente = choice["message"]
    finish_reason = choice.get("finish_reason", "")

    # Si el modelo NO invocó herramienta, retornar directo
    if finish_reason != "tool_calls" or not mensaje_asistente.get("tool_calls"):
        return (mensaje_asistente.get("content") or "").strip()

    # el modelo utiliza las herramientas
    # Agregamos el mensaje del asistente con el llamado a la herramineta al historial
    mensajes_con_tool = list(mensajes) + [mensaje_asistente]

    for tool_call in mensaje_asistente["tool_calls"]:
        nombre = tool_call["function"]["name"]
        try:
            argumentos = json.loads(tool_call["function"]["arguments"])
        except json.JSONDecodeError:
            argumentos = {}

        # Ejecutar la herramienta en Django
        resultado_json = ejecutar_herramienta_fn(nombre, argumentos)

        # Adjuntar resultado al historial
        mensajes_con_tool.append({
            "role": "tool",
            "tool_call_id": tool_call["id"],
            "content": resultado_json,
        })

    # segunda llamada recibe los resultados de la herramienta y da la respuesta
    payload2 = {
        "model": GROQ_MODEL,
        "messages": mensajes_con_tool,
        "max_tokens": max_tokens,
        "temperature": 0.4,
        "top_p": 0.9,
        "stream": False,
    }

    response2 = _hacer_request(headers, payload2)
    data2 = response2.json()
    texto_final = data2["choices"][0]["message"].get("content", "")
    return texto_final.strip()


def _hacer_request(headers: dict, payload: dict) -> requests.Response:
    """POST a GroqCloud. Lanza GroqError si hay timeout, conexión o error HTTP."""
    try:
        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
    except requests.exceptions.Timeout:
        raise GroqError("La solicitud a GroqCloud tardo demasiado. Intenta de nuevo.")
    except requests.exceptions.ConnectionError:
        raise GroqError("No se pudo conectar a GroqCloud. Verifica tu conexión a internet.")

    if response.status_code != 200:
        try:
            error_detail = response.json().get("error", {}).get("message", response.text)
        except Exception:
            error_detail = response.text
        raise GroqError(f"Error de GroqCloud ({response.status_code}): {error_detail}")

    return response