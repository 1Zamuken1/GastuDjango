"""
Definiciones de las herramientas (tools) que el modelo puede invocar.

Es la fuente unica de verdad: groq_client las envia al modelo y herramientas.py
valida cada llamada contra estos mismos esquemas antes de ejecutarla.

Reglas de diseno:
- Nombres en snake_case que digan lo que hacen; descripciones cortas que digan
  cuando usar la herramienta. Se reenvian en cada vuelta y el plan gratuito de
  Groq tiene ~8.000 tokens por minuto: cada palabra cuenta.
- additionalProperties=false en todas: un argumento que no esta en el esquema
  se rechaza en vez de ignorarse.
- Las herramientas que escriben datos (crear_movimiento, preparar_cambio) nunca
  escriben: dejan una accion pendiente que el usuario confirma con un boton.
"""

MAX_TEXTO_CORTO = 60
MAX_DESCRIPCION = 255
ANIO_MIN, ANIO_MAX = 2000, 2100
MONTO_MAX = 9999999999

_MES = {"type": "integer", "minimum": 1, "maximum": 12}
_ANIO = {"type": "integer", "minimum": ANIO_MIN, "maximum": ANIO_MAX}
_CATEGORIA = {"type": "string", "maxLength": MAX_TEXTO_CORTO, "description": "Nombre de categoría."}
_MONTO = {"type": "number", "exclusiveMinimum": 0, "maximum": MONTO_MAX}


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
        "Lista movimientos (más recientes primero) con id, fecha, monto, categoría y descripción. "
        "Úsala para historial, otros meses o para encontrar el id de 'ese gasto'.",
        {
            "tipo": {"type": "string", "enum": ["INGRESO", "EGRESO", "TODOS"]},
            "mes": _MES,
            "anio": _ANIO,
            "categoria": _CATEGORIA,
            "limite": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Por defecto 20."},
        },
    ),
    _tool(
        "obtener_resumen_periodo",
        "Ingresos, egresos y balance de un mes. Para totales o comparar meses.",
        {"mes": _MES, "anio": _ANIO},
        ["mes", "anio"],
    ),
    _tool(
        "obtener_gastos_por_categoria",
        "Egresos sumados por categoría en un mes, o en el año si se omite mes.",
        {"anio": _ANIO, "mes": _MES},
        ["anio"],
    ),
    _tool(
        "listar_categorias",
        "Categorías disponibles de un tipo. Úsala si dudas del nombre antes de crear_movimiento.",
        {"tipo": {"type": "string", "enum": ["INGRESO", "EGRESO"]}},
        ["tipo"],
    ),
    _tool(
        "obtener_estado_ahorros",
        "Metas de ahorro activas: id, meta, acumulado, cuotas pendientes y fecha límite.",
    ),
    _tool(
        "obtener_estado_presupuestos",
        "Presupuestos activos: id, límite, gastado, disponible y porcentaje consumido.",
    ),
    # ── Cálculos exactos (el modelo nunca calcula de cabeza) ───
    _tool(
        "calcular_proyeccion_meta",
        "Avance de una meta de ahorro y cuotas restantes, con un aporte extra opcional por cuota.",
        {
            "meta_id": {"type": "integer", "minimum": 1},
            "aporte_adicional_mensual": {"type": "number", "minimum": 0, "maximum": MONTO_MAX},
        },
        ["meta_id"],
    ),
    _tool(
        "calcular_ritmo_gasto",
        "Gasto diario promedio del mes actual y proyección al cierre, global o de una categoría.",
        {"categoria": _CATEGORIA},
    ),
    _tool(
        "calcular_capacidad_disponible",
        "Dinero libre del mes: ingresos menos egresos y menos cuotas de ahorro pendientes.",
    ),
    # ── Escritura con confirmación del usuario ─────────────────
    _tool(
        "crear_movimiento",
        "Prepara un gasto o ingreso para que el usuario lo confirme con un botón; no guarda nada. "
        "Solo si el usuario lo pidió.",
        {
            "tipo": {"type": "string", "enum": ["INGRESO", "EGRESO"]},
            "categoria": _CATEGORIA,
            "monto": {**_MONTO, "description": "Pesos colombianos."},
            "descripcion": {"type": "string", "maxLength": MAX_DESCRIPCION},
            "fecha": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$", "description": "AAAA-MM-DD; omitir para hoy."},
        },
        ["tipo", "categoria", "monto"],
    ),
    _tool(
        "preparar_cambio",
        "Prepara editar o eliminar un movimiento, o eliminar un presupuesto, para que el usuario lo confirme; "
        "no cambia nada. El id sale de obtener_movimientos u obtener_estado_presupuestos.",
        {
            "accion": {"type": "string", "enum": ["ELIMINAR_MOVIMIENTO", "EDITAR_MOVIMIENTO", "ELIMINAR_PRESUPUESTO"]},
            "referencia_id": {"type": "integer", "minimum": 1},
            "nuevo_monto": _MONTO,
            "nueva_descripcion": {"type": "string", "maxLength": MAX_DESCRIPCION},
            "nueva_categoria": _CATEGORIA,
        },
        ["accion", "referencia_id"],
    ),
    # ── Archivos ───────────────────────────────────────────────
    _tool(
        "generar_reporte_descarga",
        "Muestra un botón para descargar el reporte de movimientos de un mes (Excel, PDF o CSV).",
        {
            "formato": {"type": "string", "enum": ["EXCEL", "PDF", "CSV"]},
            "tipo": {"type": "string", "enum": ["INGRESO", "EGRESO", "AMBOS"]},
            "mes": _MES,
            "anio": _ANIO,
            "categoria": _CATEGORIA,
        },
    ),
]

ESQUEMAS = {t["function"]["name"]: t["function"]["parameters"] for t in TOOLS}
