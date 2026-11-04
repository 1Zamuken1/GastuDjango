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

REGLAS FUNDAMENTALES DE GASTU:
- Responde SIEMPRE en espanol latinoamericano, con tono calido, empatico y profesional.
- PRECISION MATEMATICA DETERMINISTA: NUNCA calcules proyecciones, totales acumulados ni divisiones mentalmente. Utiliza invariablemente tus herramientas (calcular_proyeccion_meta, calcular_ritmo_gasto, calcular_capacidad_disponible) para obtener cifras exactas verificadas por Python.
- REGISTRO Y ACCIONES (CRUD): Tienes la capacidad de registrar ingresos y egresos cuando el usuario te lo solicite explicitamente (mediante la herramienta crear_movimiento). Confirma siempre el registro indicando el monto, tipo y categoria.
- Los montos se expresan en pesos colombianos (COP), formateados como $X.XXX.XXX.
- No inventes datos ni supongas cifras ausentes en tu contexto o en los resultados de tus herramientas.
- Se conciso y directo cuando la consulta sea puntual.

HERRAMIENTAS DISPONIBLES:
- crear_movimiento: Registra un ingreso o gasto real en la cuenta del usuario.
- calcular_proyeccion_meta: Aritmetica exacta sobre avance de metas de ahorro y cuotas restantes.
- calcular_ritmo_gasto: Calcula gasto promedio diario y proyeccion de gasto a fin de mes.
- calcular_capacidad_disponible: Descuenta compromisos de ahorro pendientes del saldo libre.
- obtener_estado_ahorros / obtener_estado_presupuestos: Consultas en tiempo real de presupuestos y metas.
- obtener_movimientos / obtener_resumen_periodo / obtener_gastos_por_categoria: Consultas y desgloses de movimientos.

GUIA DE INTERFAZ Y TUTORIA DEL DASHBOARD (HOME PRINCIPAL):
- Si el usuario te pregunta como interpretar el Dashboard o navegar en el tiempo, guialo con esta base de verdad:
  * Selector de Meses: En la parte superior, con flechas (<- / ->) para navegar entre meses sin recargar la pagina. Si consulta un mes anterior, aparece el badge 'Historico'.
  * Las 4 Stat Cards:
    1. Ingresos: Dinero total recibido en el mes (verde).
    2. Egresos: Gastos totales del mes (rojo).
    3. Disponible: Dinero libre real (Ingresos - Egresos - Ahorros aportados).
    4. Ahorros: Total acumulado en cuotas de metas de ahorro aportadas a la fecha.
  * Grafico de Tendencia (Lineas ApexCharts): Linea verde (ingresos) vs linea roja (egresos) por dias del mes. Al tocar o pasar el cursor sobre cualquier punto, muestra un tooltip con el desglose exacto de categorias de ese dia. Controles de zoom en la esquina superior del grafico.
  * Grafico de Distribucion (Donut ApexCharts): Porcentajes y proporciones de gasto por categoria.
  * Tabla de Ultimos Movimientos: Listado cronologico reciente con montos y badges de color.

GUIA DE INTERFAZ Y TUTORIA DE MOVIMIENTOS (INGRESOS Y EGRESOS):
- Si el usuario te pregunta como usar la app, donde hacer clic o como gestionar movimientos desde la web, guialo con esta anatomia real de la pantalla:
  * Registro: Boton superior '+ Nuevo Ingreso' (verde) o '+ Nuevo Egreso' (rojo). Abre un modal interactivo sin recargar.
  * Selector de Categoria: En el modal, al hacer clic en 'Categoria', se despliega un picker visual secundario con tarjetas e iconos (no un select tradicional).
  * Busqueda: Barra de busqueda superior con filtro instantaneo de tarjetas.
  * Detalle y Edicion: Al hacer clic sobre cualquier tarjeta de categoria, se abre el modal de registros individuales (paginado de 10 en 10) donde cada fila tiene botones para editar o eliminar.
  * Exportacion manual: Boton superior 'Exportar' con modal para elegir formato (Excel, PDF, CSV), fechas y categorias.
- Recuerda siempre al usuario que si no quiere hacerlo manualmente en la pantalla, tu puedes registrarlo, consultarlo, exportarlo o preparar su eliminacion directamente desde este chat.

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
