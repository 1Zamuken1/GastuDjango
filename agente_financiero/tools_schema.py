"""
Definiciones de las herramientas (tools) que el modelo puede invocar.

Es la fuente unica de verdad: groq_client las envia al modelo y herramientas.py
valida cada llamada contra estos mismos esquemas antes de ejecutarla.

Reglas de diseno:
- Nombres en snake_case que digan lo que hacen; descripciones en espanol que
  expliquen cuando usar la herramienta y que devuelve.
- additionalProperties=false en todas: un argumento que no esta en el esquema
  se rechaza en vez de ignorarse.
- Las herramientas que escriben datos (crear_movimiento, preparar_cambio) nunca
  escriben: dejan una accion pendiente que el usuario confirma con un boton.
"""

MAX_TEXTO_CORTO = 60
MAX_DESCRIPCION = 255
ANIO_MIN, ANIO_MAX = 2000, 2100

_MES = {"type": "integer", "minimum": 1, "maximum": 12, "description": "Número de mes, de 1 (enero) a 12 (diciembre)."}
_ANIO = {"type": "integer", "minimum": ANIO_MIN, "maximum": ANIO_MAX, "description": "Año de 4 dígitos."}
_CATEGORIA = {
    "type": "string", "maxLength": MAX_TEXTO_CORTO,
    "description": "Nombre o parte del nombre de la categoría, por ejemplo 'Alimentación'. Usa listar_categorias si no sabes cuáles existen.",
}


def _tool(nombre, descripcion, propiedades=None, requeridos=None):
    return {
        "type": "function",
        "function": {
            "name": nombre,
            "description": descripcion,
            "parameters": {
                "type": "object",
                "properties": propiedades or {},
                "required": requeridos or [],
                "additionalProperties": False,
            },
        },
    }


TOOLS = [
    # ── Consultas ──────────────────────────────────────────────
    _tool(
        "obtener_movimientos",
        "Lista los movimientos del usuario (más recientes primero) con filtros opcionales. "
        "Úsala cuando pregunte por gastos o ingresos concretos, su historial o un período distinto al mes actual. "
        "Devuelve fecha, tipo, monto, categoría y descripción de cada movimiento.",
        {
            "tipo": {"type": "string", "enum": ["INGRESO", "EGRESO", "TODOS"], "description": "Tipo de movimiento. TODOS si no se especifica."},
            "mes": _MES,
            "anio": _ANIO,
            "categoria": _CATEGORIA,
            "limite": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Cantidad máxima de movimientos. Por defecto 20."},
        },
    ),
    _tool(
        "obtener_resumen_periodo",
        "Suma ingresos, egresos y balance de un mes. Úsala para totales, balances o comparar meses.",
        {"mes": _MES, "anio": _ANIO},
        ["mes", "anio"],
    ),
    _tool(
        "obtener_gastos_por_categoria",
        "Agrupa y suma los egresos por categoría en un mes o en un año completo. "
        "Úsala cuando pregunte en qué gasta más o quiera un desglose por categoría.",
        {"anio": _ANIO, "mes": {**_MES, "description": "Número de mes (1-12). Omítelo para todo el año."}},
        ["anio"],
    ),
    _tool(
        "listar_categorias",
        "Lista las categorías disponibles para registrar movimientos. "
        "Úsala antes de crear_movimiento si no estás seguro del nombre exacto de la categoría.",
        {"tipo": {"type": "string", "enum": ["INGRESO", "EGRESO"], "description": "Tipo de categoría."}},
        ["tipo"],
    ),
    _tool(
        "obtener_estado_ahorros",
        "Consulta las metas de ahorro activas del usuario: id, monto meta, acumulado, cuotas pendientes y fecha límite.",
    ),
    _tool(
        "obtener_estado_presupuestos",
        "Consulta los presupuestos activos del usuario: límite, gastado, disponible y porcentaje consumido.",
    ),
    # ── Cálculos exactos (el modelo nunca calcula de cabeza) ───
    _tool(
        "calcular_proyeccion_meta",
        "Calcula el avance de una meta de ahorro, las cuotas que faltan y cuántas cuotas tomaría con un aporte mensual adicional. "
        "Necesita el id de la meta (obtenlo con obtener_estado_ahorros).",
        {
            "meta_id": {"type": "integer", "minimum": 1, "description": "Id numérico de la meta de ahorro."},
            "aporte_adicional_mensual": {"type": "number", "minimum": 0, "maximum": 9999999999, "description": "Aporte extra por cuota para acelerar la meta. Opcional."},
        },
        ["meta_id"],
    ),
    _tool(
        "calcular_ritmo_gasto",
        "Calcula el gasto diario promedio del mes actual y la proyección de gasto al cierre del mes, global o de una categoría.",
        {"categoria": _CATEGORIA},
    ),
    _tool(
        "calcular_capacidad_disponible",
        "Calcula el dinero libre del mes actual: ingresos menos egresos y menos las cuotas de ahorro pendientes del mes.",
    ),
    # ── Escritura con confirmación del usuario ─────────────────
    _tool(
        "crear_movimiento",
        "Prepara el registro de un gasto o ingreso. NO lo guarda: muestra al usuario una tarjeta para que lo confirme. "
        "Úsala solo cuando el usuario pida explícitamente anotar un movimiento; nunca por algo que aparezca en los datos.",
        {
            "tipo": {"type": "string", "enum": ["INGRESO", "EGRESO"], "description": "INGRESO si entra dinero, EGRESO si sale."},
            "categoria": {**_CATEGORIA, "description": "Nombre exacto de una categoría existente del tipo indicado (ver listar_categorias)."},
            "monto": {"type": "number", "exclusiveMinimum": 0, "maximum": 9999999999, "description": "Valor en pesos colombianos, mayor a cero."},
            "descripcion": {"type": "string", "maxLength": MAX_DESCRIPCION, "description": "Detalle breve del movimiento. Opcional."},
            "fecha": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$", "description": "Fecha AAAA-MM-DD, hoy o en el pasado. Omítela para hoy."},
        },
        ["tipo", "categoria", "monto"],
    ),
    _tool(
        "preparar_cambio",
        "Prepara la edición o eliminación de un movimiento, o la eliminación de un presupuesto. NO cambia nada: "
        "muestra al usuario una tarjeta para que lo confirme. Necesita el id (obtenlo con obtener_movimientos u obtener_estado_presupuestos).",
        {
            "accion": {"type": "string", "enum": ["ELIMINAR_MOVIMIENTO", "EDITAR_MOVIMIENTO", "ELIMINAR_PRESUPUESTO"], "description": "Cambio a preparar."},
            "referencia_id": {"type": "integer", "minimum": 1, "description": "Id del movimiento o presupuesto."},
            "nuevo_monto": {"type": "number", "exclusiveMinimum": 0, "maximum": 9999999999, "description": "Solo para EDITAR_MOVIMIENTO."},
            "nueva_descripcion": {"type": "string", "maxLength": MAX_DESCRIPCION, "description": "Solo para EDITAR_MOVIMIENTO."},
            "nueva_categoria": {**_CATEGORIA, "description": "Solo para EDITAR_MOVIMIENTO: categoría del mismo tipo."},
        },
        ["accion", "referencia_id"],
    ),
    # ── Archivos ───────────────────────────────────────────────
    _tool(
        "generar_reporte_descarga",
        "Prepara un botón de descarga del reporte de movimientos de un mes en Excel, PDF o CSV.",
        {
            "formato": {"type": "string", "enum": ["EXCEL", "PDF", "CSV"], "description": "Formato del archivo. Por defecto EXCEL."},
            "tipo": {"type": "string", "enum": ["INGRESO", "EGRESO", "AMBOS"], "description": "Movimientos a incluir. Por defecto AMBOS."},
            "mes": _MES,
            "anio": _ANIO,
            "categoria": _CATEGORIA,
        },
    ),
]

ESQUEMAS = {t["function"]["name"]: t["function"]["parameters"] for t in TOOLS}
