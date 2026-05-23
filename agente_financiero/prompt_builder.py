"""Construye el prompt del sistema que se envía a GroqCloud (datos + historial + pregunta)."""

from datetime import date

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _formatear_cop(monto: float) -> str:
    return f"${monto:,.0f}".replace(",", ".")


def _seccion_resumen(datos: dict) -> str:
    r = datos["resumen_mensual"]
    mes_nombre = MESES_ES.get(datos["mes"], str(datos["mes"]))
    anio = datos["anio"]
    return f"""RESUMEN DEL MES ACTUAL ({mes_nombre} {anio}):
- Total ingresos: {_formatear_cop(r['total_ingresos'])}
- Total egresos: {_formatear_cop(r['total_egresos'])}
- Saldo disponible: {_formatear_cop(r['disponible'])}
- Total ahorrado este mes: {_formatear_cop(r['total_ahorrado'])}"""


def _seccion_ahorros(datos: dict) -> str:
    metas = datos["metas_ahorro"]
    if not metas:
        return "METAS DE AHORRO:\n- No tienes metas de ahorro activas."
    lineas = ["METAS DE AHORRO ACTIVAS:"]
    for m in metas:
        lineas.append(
            f"- {m['categoria']} | Meta: {_formatear_cop(m['monto_meta'])} "
            f"| Acumulado: {_formatear_cop(m['total_acumulado'])} ({m['porcentaje']}%) "
            f"| Fecha límite: {m['fecha_meta']} | Estado: {m['estado']}"
            + (f" | Cuotas pendientes: {m['cuotas_pendientes']}" if m["cuotas_pendientes"] else "")
        )
    return "\n".join(lineas)


def _seccion_presupuestos(datos: dict) -> str:
    presupuestos = datos["presupuestos"]
    if not presupuestos:
        return "PRESUPUESTOS:\n- No tienes presupuestos activos."
    lineas = ["PRESUPUESTOS ACTIVOS:"]
    for p in presupuestos:
        alerta = "ALERTA: superó el 80%" if p["alerta"] else ""
        lineas.append(
            f"- {p['categoria']} | Límite: {_formatear_cop(p['limite'])} "
            f"| Gastado: {_formatear_cop(p['gastado'])} ({p['porcentaje_usado']}%) "
            f"| Disponible: {_formatear_cop(p['disponible'])}"
            + alerta
        )
    return "\n".join(lineas)


def _seccion_programaciones(datos: dict) -> str:
    programaciones = datos["programaciones"]
    if not programaciones:
        return "PROGRAMACIONES:\n- No tienes movimientos programados."
    lineas = ["PROGRAMACIONES ACTIVAS:"]
    for p in programaciones:
        lineas.append(
            f"- {p['categoria']} {_formatear_cop(p['monto'])} cada {p['frecuencia']} "
            f"| Próxima: {p['proxima_fecha']}"
            + (f" — {p['descripcion']}" if p["descripcion"] else "")
        )
    return "\n".join(lineas)


def construir_prompt(datos: dict, pregunta: str, historial: list = None) -> list:
    """
    Construye la lista de mensajes para GroqCloud.

    Args:
        datos: Dict con datos financieros del usuario (del RecolectorDatos)
        pregunta: Mensaje actual del usuario
        historial: Lista de objetos MensajeChat ordenados cronológicamente
    """
    nombre_usuario = datos["usuario"]["nombre"]

    system_content = f"""Eres GASTU, el asistente financiero personal de {nombre_usuario}.
Tu rol es ayudar al usuario a entender y mejorar su salud financiera.

REGLAS IMPORTANTES:
- Solo puedes consultar información, NUNCA crear, editar ni eliminar datos.
- Responde SIEMPRE en español, de forma clara, amigable y directa.
- Usa los datos del usuario para dar respuestas personalizadas y precisas.
- Si te preguntan algo que no está en los datos ni puedes consultarlo con herramientas, dilo claramente.
- Cuando hagas cálculos, muestra el razonamiento paso a paso.
- Los montos están en pesos colombianos (COP). Usa el formato $X.XXX.XXX.
- No inventes datos ni supongas información que no esté en el contexto o en los resultados de herramientas.
- Sé conciso: evita respuestas largas si la pregunta es simple.
- Puedes dar consejos generales de finanzas personales cuando sea relevante.

HERRAMIENTAS DISPONIBLES:
- obtener_movimientos: filtra movimientos por tipo, mes, año, categoría y cantidad.
  Úsala SIEMPRE que el usuario pregunte por movimientos, gastos, ingresos específicos o historial.
- obtener_resumen_periodo: calcula totales de ingresos/egresos de un mes y año específico.
  Úsala cuando pregunten por balances o comparaciones de períodos.
- obtener_gastos_por_categoria: agrupa egresos por categoría en un período.
  Úsala cuando pregunten en qué gasta más o quieran un desglose.

=== CONTEXTO FINANCIERO DE {nombre_usuario.upper()} ===

{_seccion_resumen(datos)}

{_seccion_ahorros(datos)}

{_seccion_presupuestos(datos)}

{_seccion_programaciones(datos)}

Fecha de hoy: {date.today().strftime('%d/%m/%Y')}
"""

    mensajes = [{"role": "system", "content": system_content}]

    # Agregar historial previo de la conversación (da memoria al LLM)
    if historial:
        for msg in historial:
            mensajes.append({
                "role": "user" if msg.rol == "user" else "assistant",
                "content": msg.contenido,
            })

    # Mensaje actual del usuario
    mensajes.append({"role": "user", "content": pregunta})

    return mensajes