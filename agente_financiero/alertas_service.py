"""Generación de alertas financieras personalizadas vía Groq (con fallback sin IA)."""

import json
import logging
from datetime import date

import requests
from django.conf import settings

from .recolector import RecolectorDatos

logger = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

TIPOS_ALERTA = {
    "critica": {"color": "#ef4444", "icono": "🚨"},
    "advertencia": {"color": "#f97316", "icono": "⚠️"},
    "info": {"color": "#3b82f6", "icono": "💡"},
    "logro": {"color": "#22c55e", "icono": "🏆"},
    "consejo": {"color": "#a855f7", "icono": "✨"},
}

MAX_ALERTAS = 5


def _formatear_cop(monto: float) -> str:
    return f"${monto:,.0f}".replace(",", ".")
 
 
def _detectar_situaciones(datos: dict) -> list[dict]:
    """Analiza datos financieros y retorna hechos que merecen alerta (balance, presupuestos, metas)."""
    situaciones = []
    resumen = datos["resumen_mensual"]
    hoy = date.today()
 
    # 1. Balance del mes negativo o muy ajustado
    disponible = resumen["disponible"]
    ingresos   = resumen["total_ingresos"]
 
    if disponible < 0:
        situaciones.append({
            "tipo_sugerido": "critica",
            "hecho": f"El balance del mes actual es NEGATIVO: {_formatear_cop(disponible)}. "
                     f"Ingresos: {_formatear_cop(ingresos)}, Egresos: {_formatear_cop(resumen['total_egresos'])}."
        })
    elif ingresos > 0 and disponible < ingresos * 0.1:
        situaciones.append({
            "tipo_sugerido": "advertencia",
            "hecho": f"El disponible del mes ({_formatear_cop(disponible)}) es menor al 10% "
                     f"de los ingresos ({_formatear_cop(ingresos)}). Queda muy poco margen."
        })
 
    # 2. Presupuestos en alerta
    for p in datos["presupuestos"]:
        if p["porcentaje_usado"] >= 100:
            situaciones.append({
                "tipo_sugerido": "critica",
                "hecho": f"El presupuesto de '{p['categoria']}' está AGOTADO: "
                         f"gastó {_formatear_cop(p['gastado'])} de {_formatear_cop(p['limite'])} "
                         f"({p['porcentaje_usado']}%)."
            })
        elif p["porcentaje_usado"] >= 80:
            situaciones.append({
                "tipo_sugerido": "advertencia",
                "hecho": f"El presupuesto de '{p['categoria']}' está al {p['porcentaje_usado']}%: "
                         f"gastó {_formatear_cop(p['gastado'])} de {_formatear_cop(p['limite'])}. "
                         f"Solo quedan {_formatear_cop(p['disponible'])}."
            })
 
    # 3. Metas de ahorro próximas a vencer con poco progreso
    for m in datos["metas_ahorro"]:
        porcentaje = m["porcentaje"]
        try:
            fecha_meta = date.fromisoformat(
                m["fecha_meta"] if "-" in m["fecha_meta"]
                else "/".join(reversed(m["fecha_meta"].split("/")))
            )
            dias_restantes = (fecha_meta - hoy).days
        except Exception:
            dias_restantes = None
 
        if dias_restantes is not None and dias_restantes <= 30 and porcentaje < 70:
            situaciones.append({
                "tipo_sugerido": "advertencia",
                "hecho": f"La meta '{m['categoria']}' vence en {dias_restantes} días "
                         f"y solo lleva el {porcentaje}% ({_formatear_cop(m['total_acumulado'])} "
                         f"de {_formatear_cop(m['monto_meta'])})."
            })
        elif porcentaje >= 90:
            situaciones.append({
                "tipo_sugerido": "logro",
                "hecho": f"La meta '{m['categoria']}' está casi completa: {porcentaje}% alcanzado "
                         f"({_formatear_cop(m['total_acumulado'])} de {_formatear_cop(m['monto_meta'])})."
            })
        elif porcentaje == 0 and m["estado"] != "SIN_INICIAR":
            situaciones.append({
                "tipo_sugerido": "info",
                "hecho": f"La meta '{m['categoria']}' no tiene ningún aporte aún. "
                         f"Objetivo: {_formatear_cop(m['monto_meta'])}."
            })
 
    # 4. Cuotas de ahorro pendientes
    cuotas_totales = sum(m.get("cuotas_pendientes", 0) or 0 for m in datos["metas_ahorro"])
    if cuotas_totales > 0:
        situaciones.append({
            "tipo_sugerido": "info",
            "hecho": f"Tienes {cuotas_totales} cuota(s) de ahorro pendiente(s) de pagar."
        })
 
    # 5. Sin ahorros registrados este mes (si hay ingresos)
    if ingresos > 0 and resumen.get("total_ahorrado", 0) == 0 and not datos["metas_ahorro"]:
        situaciones.append({
            "tipo_sugerido": "consejo",
            "hecho": f"Este mes tienes ingresos de {_formatear_cop(ingresos)} pero no hay "
                     f"ningún ahorro registrado. Podrías empezar una meta de ahorro."
        })
 
    # 6. Si todo está bien (logro general)
    if not situaciones and disponible > 0:
        situaciones.append({
            "tipo_sugerido": "logro",
            "hecho": f"Las finanzas del mes van bien: disponible {_formatear_cop(disponible)} "
                     f"de {_formatear_cop(ingresos)} de ingresos. Sin alertas críticas."
        })
 
    return situaciones[:MAX_ALERTAS]
 
 
def _construir_prompt_alertas(nombre: str, situaciones: list[dict], mes: int, anio: int) -> list:
    """Prompt para que Groq convierta hechos en alertas personalizadas."""
    MESES_ES = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
    }
    mes_nombre = MESES_ES.get(mes, str(mes))
 
    hechos_texto = "\n".join(
        f"{i+1}. [{s['tipo_sugerido'].upper()}] {s['hecho']}"
        for i, s in enumerate(situaciones)
    )
 
    system_prompt = """Eres GASTU, un asistente financiero personal amigable y directo.
Tu tarea es convertir hechos financieros crudos en alertas cortas, claras y motivadoras.
 
REGLAS:
- Responde SOLO con un JSON válido, sin markdown, sin texto extra.
- El JSON debe ser una lista de objetos con exactamente estos campos:
  {
    "tipo": "critica" | "advertencia" | "info" | "logro" | "consejo",
    "titulo": "Título corto y llamativo (máximo 6 palabras)",
    "mensaje": "Mensaje personalizado, directo, máximo 2 oraciones. Usa el nombre del usuario.",
    "accion": "Sugerencia de acción concreta en 1 oración corta (puede ser null si es un logro)"
  }
- Usa el nombre del usuario de forma natural (no en cada oración).
- Sé empático, no alarmista. Informa, no regañes.
- Para logros: celebra genuinamente.
- Para críticas/advertencias: sé directo pero constructivo.
- Respeta el tipo sugerido de cada hecho."""
 
    user_content = f"""Usuario: {nombre}
Período: {mes_nombre} {anio}
 
Hechos financieros detectados:
{hechos_texto}
 
Convierte estos hechos en alertas personalizadas. Responde SOLO con el JSON."""
 
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_content},
    ]
 
 
def generar_alertas(usuario) -> list[dict]:
    """Genera alertas financieras del usuario: recolecta datos, detecta situaciones, llama a Groq y combina con metadatos de estilo."""
    # 1. Recolectar datos
    recolector = RecolectorDatos(usuario)
    datos = recolector.recolectar_todo()
    nombre = datos["usuario"]["nombre"]
    mes    = datos["mes"]
    anio   = datos["anio"]
 
    # 2. Detectar situaciones
    situaciones = _detectar_situaciones(datos)
    if not situaciones:
        return []
 
    # 3. Construir prompt y llamar a Groq
    mensajes = _construir_prompt_alertas(nombre, situaciones, mes, anio)
 
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        logger.warning("[GASTU Alertas] GROQ_API_KEY no configurada, usando alertas sin IA.")
        return _alertas_fallback(situaciones)
 
    try:
        response = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": mensajes,
                "max_tokens": 1024,
                "temperature": 0.5,
                "stream": False,
            },
            timeout=20,
        )
        response.raise_for_status()
        contenido = response.json()["choices"][0]["message"]["content"].strip()
 
        # Limpiar posibles backticks de markdown
        contenido = contenido.replace("```json", "").replace("```", "").strip()
        alertas_raw = json.loads(contenido)
 
    except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
        logger.error(f"[GASTU Alertas] Error generando alertas con IA: {e}")
        return _alertas_fallback(situaciones)
 
    # 4. Combinar con metadatos de estilo
    alertas_finales = []
    for alerta in alertas_raw:
        tipo = alerta.get("tipo", "info")
        meta = TIPOS_ALERTA.get(tipo, TIPOS_ALERTA["info"])
        alertas_finales.append({
            "tipo":    tipo,
            "color":   meta["color"],
            "icono":   meta["icono"],
            "titulo":  alerta.get("titulo", ""),
            "mensaje": alerta.get("mensaje", ""),
            "accion":  alerta.get("accion"),
        })
 
    return alertas_finales
 
 
def _alertas_fallback(situaciones: list[dict]) -> list[dict]:
    """Alertas sin IA (fallback para cuando Groq no responde)."""
    alertas = []
    for s in situaciones:
        tipo = s["tipo_sugerido"]
        meta = TIPOS_ALERTA.get(tipo, TIPOS_ALERTA["info"])
        alertas.append({
            "tipo":    tipo,
            "color":   meta["color"],
            "icono":   meta["icono"],
            "titulo":  "Aviso financiero",
            "mensaje": s["hecho"],
            "accion":  None,
        })
    return alertas