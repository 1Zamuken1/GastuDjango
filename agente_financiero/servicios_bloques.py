"""
servicios_bloques.py — Ensamblador de Bloques Estructurados para Agente Financiero GASTU
Genera bloques tipados (medidor, cifras, libreta, consejo, siguientes, procedencia)
con cálculo determinista de backend y respaldo cuando no hay cuota de IA.
"""

from decimal import Decimal
from datetime import date
import calendar
import logging
from django.db.models import Sum, Q

from movimientos.models import Movimiento
from presupuesto.models import Presupuesto
from presupuesto.services import obtener_estados_presupuestos
from categorias.models import Categoria

logger = logging.getLogger(__name__)

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}


def formatear_cop(valor):
    """Retorna un entero como formato COP: $517.000"""
    v = int(round(valor or 0))
    return f"${v:,}".replace(",", ".")


def calcular_metricas_presupuesto(usuario, categoria_nombre=None, mes=None, anio=None):
    """
    Calcula métricas matemáticas exactas para un presupuesto según la sección 7.4 del brief:
    - consumo_pct = gastado / limite * 100
    - disponible = max(limite - gastado, 0)
    - dias_transcurridos = dia_actual (mínimo 1)
    - dias_restantes = dias_del_mes - dia_actual + 1
    - gasto_diario = gastado / dias_transcurridos
    - maximo_diario = disponible / dias_restantes
    - dias_hasta_limite = disponible / gasto_diario (si gasto_diario > 0)
    - estado: ok | alerta | excedido
    """
    hoy = date.today()
    mes = mes or hoy.month
    anio = anio or hoy.year
    dia_actual = hoy.day if (hoy.month == mes and hoy.year == anio) else 1

    dias_del_mes = calendar.monthrange(anio, mes)[1]
    dias_transcurridos = max(dia_actual, 1)
    dias_restantes = max(dias_del_mes - dia_actual + 1, 1)

    # Buscar presupuestos activos
    pres_qs = Presupuesto.objects.filter(
        usuario=usuario, is_activo=True
    ).select_related("categoria")

    presupuesto = None
    if categoria_nombre:
        presupuesto = pres_qs.filter(categoria__nombre__icontains=categoria_nombre.strip()).first()
    if not presupuesto:
        # Tomar el primer presupuesto con mayor consumo o el primero activo
        presupuesto = pres_qs.first()

    if not presupuesto:
        return None

    cat_nombre = presupuesto.categoria.nombre
    limite = float(presupuesto.limite)

    # Calcular total gastado en el rango
    total_gastado = Movimiento.objects.filter(
        usuario=usuario,
        categoria=presupuesto.categoria,
        tipo="EGRESO",
        fecha_registro__date__range=(presupuesto.fecha_inicio, presupuesto.fecha_fin)
    ).aggregate(total=Sum("monto"))["total"] or Decimal("0")
    gastado = float(total_gastado)

    consumo_pct = round((gastado / limite * 100), 1) if limite > 0 else 0.0
    disponible = max(limite - gastado, 0.0)
    exceso = max(gastado - limite, 0.0)

    gasto_diario = gastado / dias_transcurridos if dias_transcurridos > 0 else 0.0
    maximo_diario = disponible / dias_restantes if dias_restantes > 0 else 0.0

    dias_hasta_limite = round(disponible / gasto_diario) if gasto_diario > 0 else 999

    umbral_pct = 80
    if consumo_pct >= 100:
        estado = "excedido"
        animo = "alerta"
    elif consumo_pct >= umbral_pct:
        estado = "alerta"
        animo = "alerta"
    else:
        estado = "ok"
        animo = "positivo"

    return {
        "categoria": cat_nombre,
        "categoria_id": presupuesto.categoria.id,
        "limite": int(round(limite)),
        "gastado": int(round(gastado)),
        "disponible": int(round(disponible)),
        "exceso": int(round(exceso)),
        "consumo_pct": int(round(consumo_pct)),
        "umbral_pct": umbral_pct,
        "dias_transcurridos": dias_transcurridos,
        "dias_restantes": dias_restantes,
        "gasto_diario": int(round(gasto_diario)),
        "maximo_diario": int(round(maximo_diario)),
        "dias_hasta_limite": int(dias_hasta_limite),
        "estado": estado,
        "animo": animo,
        "mes_nombre": MESES_ES.get(mes, ""),
        "anio": anio,
        "fecha_inicio": presupuesto.fecha_inicio,
        "fecha_fin": presupuesto.fecha_fin,
    }


def generar_consejo_plantilla(metricas):
    """Genera el consejo de respaldo determinista con números exactos."""
    estado = metricas["estado"]
    cat = metricas["categoria"]
    gasto_diario = formatear_cop(metricas["gasto_diario"])
    maximo_diario = formatear_cop(metricas["maximo_diario"])
    dias_lim = metricas["dias_hasta_limite"]
    mes_nombre = metricas["mes_nombre"]

    if estado == "excedido":
        exceso = formatear_cop(metricas["exceso"])
        return (
            f"Has sobrepasado el límite de {cat} por {exceso}. "
            f"Para no afectar tu ahorro mensual, te recomiendo frenar gastos no esenciales en este rubro durante lo que queda de {mes_nombre}."
        )
    elif estado == "alerta":
        return (
            f"Llevas un ritmo de {gasto_diario} diarios; a este ritmo el límite se agotará en unos {dias_lim} días. "
            f"Para cerrar {mes_nombre} dentro de lo planeado, procura no superar los {maximo_diario} por día."
        )
    else:
        return (
            f"Vas a un ritmo saludable de {gasto_diario} por día. "
            f"Tienes margen de hasta {maximo_diario} diarios para mantener tu presupuesto de {cat} bajo control."
        )


def ensamblar_bloques_presupuesto(usuario, categoria_nombre=None, consejo_texto=None, origen_consejo="modelo"):
    """
    Construye el paquete completo de bloques según el esquema 7.3:
    [titular, medidor, cifras, consejo, libreta, procedencia, siguientes]
    """
    metricas = calcular_metricas_presupuesto(usuario, categoria_nombre)
    if not metricas:
        return None, "neutral", ""

    cat = metricas["categoria"]
    pct = metricas["consumo_pct"]
    estado = metricas["estado"]
    animo = metricas["animo"]

    # 1. Titular
    if estado == "excedido":
        titular_texto = f"Te pasaste del presupuesto de {cat} por {formatear_cop(metricas['exceso'])}."
    elif estado == "alerta":
        titular_texto = f"Vas al {pct}% de tu presupuesto en {cat}."
    else:
        titular_texto = f"Vas bien en {cat}: llevas el {pct}% de tu presupuesto."

    # 2. Medidor
    bloque_medidor = {
        "tipo": "medidor",
        "categoria": cat,
        "consumo_pct": pct,
        "umbral_pct": metricas["umbral_pct"],
        "limite": metricas["limite"],
        "gastado": metricas["gastado"],
    }

    # 3. Cifras
    estado_cifra = "ok" if estado == "ok" else ("danger" if estado == "excedido" else "warn")
    bloque_cifras = {
        "tipo": "cifras",
        "columnas": [
            {
                "etiqueta": "Te quedan" if estado != "excedido" else "Sobrepasado",
                "valor": metricas["disponible"] if estado != "excedido" else metricas["exceso"],
                "estado": estado_cifra,
            },
            {
                "etiqueta": "Máximo por día",
                "valor": metricas["maximo_diario"],
                "estado": "ok" if estado == "ok" else "warn",
            }
        ]
    }

    # 4. Consejo
    if not consejo_texto or len(consejo_texto.strip()) == 0:
        consejo_final = generar_consejo_plantilla(metricas)
        origen_consejo = "plantilla"
    else:
        # Limpiar texto del modelo si incluye "Mi consejo:" repetido
        consejo_limpio = consejo_texto.strip()
        for prefix in ["**Mi consejo.**", "**Mi consejo:**", "Mi consejo:", "Mi consejo."]:
            if consejo_limpio.startswith(prefix):
                consejo_limpio = consejo_limpio[len(prefix):].strip()
        consejo_final = consejo_limpio

    bloque_consejo = {
        "tipo": "consejo",
        "texto": consejo_final,
        "origen": origen_consejo,
    }

    # 5. Libreta (movimientos recientes en esta categoría)
    movimientos_qs = Movimiento.objects.filter(
        usuario=usuario,
        categoria_id=metricas["categoria_id"],
        tipo="EGRESO",
        fecha_registro__date__range=(metricas["fecha_inicio"], metricas["fecha_fin"])
    ).order_by("-fecha_registro")

    total_filas = movimientos_qs.count()
    filas = []
    for m in movimientos_qs[:5]:
        filas.append({
            "fecha": m.fecha_registro.strftime("%Y-%m-%d"),
            "concepto": m.descripcion or cat,
            "monto": int(round(float(m.monto))),
            "movimiento": "EGRESO",
        })

    bloque_libreta = {
        "tipo": "libreta",
        "titulo": f"Movimientos en {cat}",
        "filas": filas,
        "mostradas": len(filas),
        "total_filas": total_filas,
        "total": {
            "etiqueta": f"Total {cat}",
            "valor": metricas["gastado"]
        }
    }

    # 6. Procedencia
    procedencia_texto = f"Cifras calculadas con tus movimientos de {metricas['mes_nombre']} {metricas['anio']}."
    bloque_procedencia = {
        "tipo": "procedencia",
        "texto": procedencia_texto
    }

    # 7. Siguientes (Atajos rápidos de continuación)
    otros_presupuestos = Presupuesto.objects.filter(
        usuario=usuario, is_activo=True
    ).exclude(categoria_id=metricas["categoria_id"])[:1]

    items_siguientes = [
        {"etiqueta": "¿Qué pasa si supero mi límite?", "pregunta": f"¿Qué pasa si supero el presupuesto de {cat}?"}
    ]
    if otros_presupuestos.exists():
        otra_cat = otros_presupuestos.first().categoria.nombre
        items_siguientes.append({
            "etiqueta": f"Ver presupuesto de {otra_cat}",
            "pregunta": f"Cómo va mi presupuesto de {otra_cat}"
        })
    else:
        items_siguientes.append({
            "etiqueta": "Ver todos mis presupuestos",
            "pregunta": "¿Cómo van todos mis presupuestos activos este mes?"
        })

    bloque_siguientes = {
        "tipo": "siguientes",
        "items": items_siguientes
    }

    bloques = [
        {"tipo": "titular", "texto": titular_texto},
        bloque_medidor,
        bloque_cifras,
        bloque_consejo,
        bloque_libreta,
        bloque_procedencia,
        bloque_siguientes,
    ]

    return bloques, animo, procedencia_texto


def ensamblar_bloques_movimientos(usuario, tipo="EGRESO", categoria_nombre=None, limite=6):
    """Ensambla una respuesta centrada en la Libreta Contable de movimientos."""
    hoy = date.today()
    qs = Movimiento.objects.filter(
        usuario=usuario, activo=True
    ).select_related("categoria").order_by("-fecha_registro")

    if tipo and tipo != "TODOS":
        qs = qs.filter(tipo=tipo)
    if categoria_nombre:
        qs = qs.filter(categoria__nombre__icontains=categoria_nombre.strip())

    total_filas = qs.count()
    items = qs[:limite]

    filas = []
    total_suma = 0
    for m in items:
        val = int(round(float(m.monto)))
        total_suma += val
        filas.append({
            "fecha": m.fecha_registro.strftime("%Y-%m-%d"),
            "concepto": m.descripcion or (m.categoria.nombre if m.categoria else "Sin categoría"),
            "monto": val,
            "movimiento": m.tipo,
        })

    titulo_libreta = f"Últimos {len(filas)} movimientos" if not categoria_nombre else f"Movimientos en {categoria_nombre}"
    mes_nombre = MESES_ES.get(hoy.month, "")

    bloques = [
        {"tipo": "titular", "texto": f"Aquí tienes tus movimientos recientes de {mes_nombre}."},
        {
            "tipo": "libreta",
            "titulo": titulo_libreta,
            "filas": filas,
            "mostradas": len(filas),
            "total_filas": total_filas,
            "total": {
                "etiqueta": "Total mostrado",
                "valor": total_suma
            }
        },
        {
            "tipo": "procedencia",
            "texto": f"Datos en tiempo real de tu cuenta Gastu al {hoy.strftime('%d/%m/%Y')}."
        },
        {
            "tipo": "siguientes",
            "items": [
                {"etiqueta": "¿Cómo van mis presupuestos?", "pregunta": "¿Cómo van mis presupuestos este mes?"},
                {"etiqueta": "¿Cuál es mi saldo disponible?", "pregunta": "¿Cuál es mi saldo disponible actual?"}
            ]
        }
    ]

    return bloques, "neutral", f"Historial al {hoy.strftime('%d/%m/%Y')}"


def detectar_y_ensamblar_bloques(usuario, pregunta, respuesta_llm=None):
    """
    Detecta si la consulta del usuario corresponde a un patrón financiero estructurado
    (presupuesto, movimientos, etc.) y devuelve los bloques de presentación premium.
    Si no corresponde a un patrón estructurado o no hay presupuesto configurado, retorna None.
    """
    p_lower = pregunta.lower().strip()

    # 1. Consulta sobre presupuestos
    if "presupuesto" in p_lower:
        # Detectar posible categoría en los presupuestos activos del usuario
        categorias_presupuesto = Presupuesto.objects.filter(
            usuario=usuario, is_activo=True
        ).values_list("categoria__nombre", flat=True)
        cat_match = None
        for c in categorias_presupuesto:
            if c and c.lower() in p_lower:
                cat_match = c
                break

        bloques, animo, procedencia = ensamblar_bloques_presupuesto(
            usuario=usuario,
            categoria_nombre=cat_match,
            consejo_texto=respuesta_llm,
            origen_consejo="modelo" if respuesta_llm else "plantilla"
        )
        if bloques:
            return bloques, animo, procedencia

    # 2. Consulta sobre movimientos recientes / gastos recientes
    if any(k in p_lower for k in ["últimos movimientos", "ultimos movimientos", "mis movimientos", "últimos gastos", "ultimos gastos"]):
        bloques, animo, procedencia = ensamblar_bloques_movimientos(usuario=usuario)
        if bloques:
            return bloques, animo, procedencia

    return None, "neutral", ""
