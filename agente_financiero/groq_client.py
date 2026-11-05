"""Cliente HTTP para GroqCloud con soporte de tool calling."""

import json
import requests
from django.conf import settings

import os
GROQ_MODEL = getattr(settings, "GROQ_MODEL", os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqError(Exception):
    """Error de conexión o respuesta con GroqCloud."""
    pass


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calcular_proyeccion_meta",
            "description": "Calcula matematicamente el avance, cuotas restantes y fecha estimada para cumplir una meta de ahorro especifica.",
            "parameters": {
                "type": "object",
                "properties": {
                    "meta_id": {
                        "type": "integer",
                        "description": "ID numerico de la meta de ahorro."
                    },
                    "aporte_adicional_mensual": {
                        "type": ["number", "null"],
                        "description": "Monto voluntario adicional a aportar para acelerar el cumplimiento (opcional)."
                    }
                },
                "required": ["meta_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_ritmo_gasto",
            "description": "Calcula con precision matematica el gasto diario promedio y la proyeccion de cierre a fin de mes para evitar sobregastos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": {
                        "type": ["string", "null"],
                        "description": "Nombre parcial de la categoria a evaluar (opcional o null para gasto global)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_capacidad_disponible",
            "description": "Calcula con formulas exactas en Python el disponible libre del usuario deduciendo compromisos fijos y cuotas de ahorro.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "crear_movimiento",
            "description": "Registra un nuevo gasto o ingreso en la cuenta del usuario autenticado de forma segura.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo": {
                        "type": "string",
                        "enum": ["INGRESO", "EGRESO"],
                        "description": "Tipo de movimiento a registrar."
                    },
                    "categoria": {
                        "type": "string",
                        "description": "Nombre de la categoria (ej. Alimentacion, Transporte, Salario, etc.)."
                    },
                    "monto": {
                        "type": "number",
                        "description": "Valor monetario del movimiento (debe ser mayor a cero)."
                    },
                    "descripcion": {
                        "type": "string",
                        "description": "Detalle explicativo breve opcional del movimiento."
                    }
                },
                "required": ["tipo", "categoria", "monto"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_estado_ahorros",
            "description": "Consulta todas las metas de ahorro activas del usuario, sus montos acumulados y estados de cuotas.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_estado_presupuestos",
            "description": "Consulta todos los presupuestos activos del usuario con sus limites, gastos actuales y porcentajes consumidos.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },    {
        "type": "function",
        "function": {
            "name": "preparar_confirmacion_accion",
            "description": "Intercepta y prepara la confirmacion interactiva (Human-in-the-Loop) obligatoria antes de eliminar o modificar datos sensibles del usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_accion": {
                        "type": "string",
                        "enum": ["ELIMINAR_MOVIMIENTO", "EDITAR_MOVIMIENTO", "ELIMINAR_PRESUPUESTO"],
                        "description": "Tipo de accion destructiva a preparar."
                    },
                    "referencia_id": {
                        "type": "integer",
                        "description": "ID del movimiento o presupuesto a afectar."
                    },
                    "detalles_modificacion": {
                        "type": "object",
                        "description": "Diccionario con los campos a alterar si es una edicion (monto, categoria, descripcion)."
                    },
                    "motivo": {
                        "type": "string",
                        "description": "Explicacion breve de la accion solicitada por el usuario."
                    }
                },
                "required": ["tipo_accion", "referencia_id"]
            }
        }
    },    {
        "type": "function",
        "function": {
            "name": "generar_reporte_descarga",
            "description": "Genera el enlace de descarga directa de reportes oficiales de movimientos en Excel (.xlsx), PDF (.pdf) o CSV (.csv).",
            "parameters": {
                "type": "object",
                "properties": {
                    "formato": {
                        "type": "string",
                        "enum": ["EXCEL", "PDF", "CSV"],
                        "description": "Formato del documento solicitado. Por defecto usa EXCEL."
                    },
                    "tipo": {
                        "type": "string",
                        "enum": ["INGRESO", "EGRESO", "AMBOS"],
                        "description": "Filtro de movimientos: INGRESO, EGRESO o AMBOS (por defecto)."
                    },
                    "mes": {
                        "type": "integer",
                        "description": "Numero del mes (1-12). Por defecto usa el mes actual."
                    },
                    "anio": {
                        "type": "integer",
                        "description": "Ano de 4 digitos. Por defecto usa el ano actual."
                    },
                    "categoria": {
                        "type": "string",
                        "description": "Nombre de categoria opcional para filtrar el reporte."
                    }
                },
                "required": []
            }
        }
    },    {
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
                        "type": ["integer", "null"],
                        "description": "Número de mes (1-12). Omitir o null si no se especifica.",
                    },
                    "anio": {
                        "type": ["integer", "null"],
                        "description": "Año de 4 dígitos. Omitir o null si no se especifica.",
                    },
                    "categoria": {
                        "type": ["string", "null"],
                        "description": "Nombre parcial de la categoría a filtrar (opcional o null).",
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
                        "type": ["integer", "null"],
                        "description": "Número de mes (1-12). Omitir o null para todo el año.",
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

def preguntar_a_groq(mensajes: list, ejecutar_herramienta_fn, max_tokens: int = 2048, max_vueltas: int = 3) -> str:
    """Envía mensajes a Groq, maneja tool calling en bucle iterativo y retorna la respuesta final."""
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

    mensajes_actuales = list(mensajes)

    for vuelta in range(max_vueltas):
        es_ultima = (vuelta == max_vueltas - 1)

        payload = {
            "model": GROQ_MODEL,
            "messages": mensajes_actuales,
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

        # Si el modelo NO invocó herramientas o terminó, retornar el contenido
        if finish_reason != "tool_calls" or not mensaje_asistente.get("tool_calls"):
            return (mensaje_asistente.get("content") or "").strip()

        # Adjuntar llamada del asistente al historial de la conversación
        mensajes_actuales.append(mensaje_asistente)

        # Ejecutar cada herramienta solicitada
        for tool_call in mensaje_asistente["tool_calls"]:
            nombre = tool_call["function"]["name"]
            try:
                argumentos = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError:
                argumentos = {}

            # Limpiar argumentos con valor None para no causar problemas internos
            argumentos_limpios = {k: v for k, v in argumentos.items() if v is not None}

            resultado_json = ejecutar_herramienta_fn(nombre, argumentos_limpios)

            mensajes_actuales.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": resultado_json,
            })

    return (mensaje_asistente.get("content") or "").strip()


def _hacer_request(headers: dict, payload: dict, max_intentos: int = 2) -> requests.Response:
    """POST a GroqCloud con manejo de reintentos ante rate limits (429) y timeout."""
    import time
    import re

    intento = 0
    while intento < max_intentos:
        intento += 1
        try:
            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )
        except requests.exceptions.Timeout:
            raise GroqError("La solicitud a GroqCloud tardó demasiado. Intenta de nuevo.")
        except requests.exceptions.ConnectionError:
            raise GroqError("No se pudo conectar a GroqCloud. Verifica tu conexión a internet.")

        if response.status_code == 200:
            return response

        # Manejo de Rate Limit (HTTP 429)
        if response.status_code == 429 and intento < max_intentos:
            try:
                error_detail = response.json().get("error", {}).get("message", response.text)
            except Exception:
                error_detail = response.text

            # Extraer tiempo sugerido por Groq (ej: "Please try again in 4.2s")
            match = re.search(r'try again in ([\d\.]+)s', error_detail)
            espera = 5.0
            if match:
                try:
                    espera = min(float(match.group(1)) + 0.5, 8.0)
                except ValueError:
                    pass
            time.sleep(espera)
            continue

        # Si no fue 200 y no se pudo reintentar
        try:
            error_detail = response.json().get("error", {}).get("message", response.text)
        except Exception:
            error_detail = response.text

        if response.status_code == 429:
            match = re.search(r'try again in ([\d\.]+)s', error_detail)
            segundos = f" unos {int(float(match.group(1)))} segundos" if match else " un momento"
            raise GroqError(f"Límite de consultas alcanzado temporalmente. Por favor espera{segundos} antes de volver a preguntar.")

        raise GroqError(f"Error del servicio de IA ({response.status_code}): {error_detail}")

    return response