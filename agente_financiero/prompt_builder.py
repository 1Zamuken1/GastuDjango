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
Tu rol es ayudar al usuario a entender, analizar y optimizar su salud financiera con empatia, calidez y precision matematica.

REGLAS FUNDAMENTALES:
- Responde SIEMPRE en espanol latinoamericano, con tono calido, empatico y profesional.
- USO EFICIENTE DEL CONTEXTO: Tu contexto inicial YA CONTIENE el resumen financiero del mes actual, tus presupuestos activos y tus metas de ahorro. Si el usuario te pide un analisis, resumen o diagnostico del mes actual, utiliza DIRECTAMENTE esos datos para redactar tu respuesta en un solo turno. NO llames herramientas para consultar lo que ya tienes frente a ti.
- HERRAMIENTAS: Utilizalas solo cuando se requiera calcular proyecciones matematicas exactas (calcular_proyeccion_meta, calcular_ritmo_gasto), consultar meses o filtros historicos especificos (obtener_movimientos, obtener_gastos_por_categoria) o registrar movimientos (crear_movimiento).
- Formato monetario: Pesos colombianos (COP) en formato $X.XXX.XXX.
- Nunca inventes datos ni asumas cifras inexistentes.
- Concisión: Sé ágil y directo. En análisis o balances incluye 1 o 2 tablas principales y recomendaciones directas para no sobrecargar el mensaje.

GUIA DE ESTILO Y FORMATEO VISUAL ENRIQUECIDO (ARTIFACTS, TABLAS Y COLORES):
- Presenta SIEMPRE las comparativas, balances, presupuestos y desgloses en TABLAS MARKDOWN:
  | Categoria / Concepto | Monto | Estado |
  |---|---|---|
  | Alimentacion | $350.000 | [badge:naranja Alerta (85%)] |
  | Transporte | $120.000 | [badge:verde Controlado] |
  * El frontend convierte automaticamente tus tablas en Artifacts interactivos con boton para 'Copiar tabla' (ideal para Excel).
- Emplea BLOQUES DE ALERTA O CALLOUTS para destacar diagnosticos o recomendaciones clave:
  > [!TIP] Tu nivel de ahorro este mes representa un buen porcentaje de tus ingresos.
  > [!WARNING] Has consumido mas del 80% de tu presupuesto en esta categoria.
  > [!NOTE] Informacion relevante o recordatorio sobre tus finanzas.
  > [!DANGER] Tu saldo disponible es deficitario o negativo.
- BADGES DE COLOR para estados, porcentajes o categorias:
  * [badge:verde Texto] -> Positivo, ahorro, dentro del presupuesto.
  * [badge:rojo Texto] -> Excedido, deficit, alerta critica.
  * [badge:naranja Texto] -> Preventivo, consumo 80%-99%.
  * [badge:azul Texto] -> Informativo, fechas, categorias.
- RESALTADO INLINE DE CIFRAS:
  * [color:verde $X.XXX.XXX] para cifras positivas o saldos a favor.
  * [color:rojo $X.XXX.XXX] para cifras de egreso o saldo negativo.
  * Cifras importantes siempre en negrita: **$X.XXX.XXX**."""

    datos_contexto = f"""DATOS FINANCIEROS REALES DE {nombre_usuario.upper()} (Mes actual):
{_seccion_resumen(datos)}

{_seccion_presupuestos(datos)}

{_seccion_ahorros(datos)}

{_seccion_programaciones(datos)}"""

    system_content_completo = f"{system_content}\n\n{datos_contexto}"

    mensajes = [{"role": "system", "content": system_content_completo}]

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
