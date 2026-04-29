"""
agente_financiero/herramientas.py

Ejecutor de herramientas (tools) que el LLM puede invocar.
Cada herramienta hace queries reales al ORM filtradas por usuario.
SOLO LECTURA — nunca crea, edita ni elimina registros.
"""

import json
import logging
from datetime import date
from decimal import Decimal

from movimientos.models import Movimiento

logger = logging.getLogger(__name__)

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


class EjecutorHerramientas:
    """
    Recibe el nombre de la herramienta y los argumentos que eligió el LLM,
    ejecuta el query correspondiente y retorna un JSON string con los resultados.

    Uso:
        ejecutor = EjecutorHerramientas(request.user)
        resultado = ejecutor.ejecutar("obtener_movimientos", {"mes": 3, "anio": 2025})
    """

    def __init__(self, usuario):
        self.usuario = usuario
        self.hoy = date.today()

    def ejecutar(self, nombre: str, argumentos: dict) -> str:
        """
        Dispatcher principal. Retorna siempre un JSON string.
        Si la herramienta no existe o falla, retorna un JSON con error.
        """
        handlers = {
            "obtener_movimientos": self._obtener_movimientos,
            "obtener_resumen_periodo": self._obtener_resumen_periodo,
            "obtener_gastos_por_categoria": self._obtener_gastos_por_categoria,
        }

        handler = handlers.get(nombre)
        if not handler:
            return json.dumps({"error": f"Herramienta '{nombre}' no reconocida."})

        try:
            resultado = handler(**argumentos)
            return json.dumps(resultado, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[GASTU] Error en herramienta '{nombre}' args={argumentos}: {e}")
            return json.dumps({"error": f"Error al ejecutar la consulta: {str(e)}"})

    # -------------------------------------------------------------------------
    # Herramienta obtener_movimientos
    # -------------------------------------------------------------------------

    def _obtener_movimientos(
        self,
        tipo: str = "TODOS",
        mes: int = None,
        anio: int = None,
        categoria: str = None,
        limite: int = 20,
    ) -> dict:
        """
        Retorna movimientos filtrados por los parámetros que eligió el modelo.
        """
        limite = min(max(int(limite), 1), 100)  # Entre 1 y 100

        qs = Movimiento.objects.filter(
            usuario=self.usuario, activo=True
        ).select_related("categoria").order_by("-fecha_registro")

        if tipo and tipo != "TODOS":
            qs = qs.filter(tipo=tipo)

        if mes:
            qs = qs.filter(fecha_registro__month=int(mes))

        if anio:
            qs = qs.filter(fecha_registro__year=int(anio))

        if categoria:
            qs = qs.filter(categoria__nombre__icontains=categoria)

        qs = qs[:limite]

        movimientos = [
            {
                "fecha": m.fecha_registro.strftime("%d/%m/%Y"),
                "tipo": m.tipo,
                "monto": float(m.monto),
                "categoria": m.categoria.nombre if m.categoria else "Sin categoría",
                "descripcion": m.descripcion or "",
            }
            for m in qs
        ]

        # Armar descripción del filtro aplicado para que el modelo entienda el contexto
        filtros_desc = []
        if tipo != "TODOS":
            filtros_desc.append(f"tipo={tipo}")
        if mes:
            filtros_desc.append(f"mes={MESES_ES.get(mes, mes)}")
        if anio:
            filtros_desc.append(f"año={anio}")
        if categoria:
            filtros_desc.append(f"categoría contiene '{categoria}'")

        return {
            "filtros_aplicados": filtros_desc or ["ninguno (todos los movimientos)"],
            "total_registros": len(movimientos),
            "movimientos": movimientos,
        }

    # -------------------------------------------------------------------------
    # Herramienta obtener_resumen_periodo
    # -------------------------------------------------------------------------

    def _obtener_resumen_periodo(self, mes: int, anio: int) -> dict:
        """
        Calcula ingresos, egresos y balance de un mes/año específico.
        """
        qs = Movimiento.objects.filter(
            usuario=self.usuario,
            activo=True,
            fecha_registro__month=int(mes),
            fecha_registro__year=int(anio),
        )

        total_ingresos = sum(
            m.monto for m in qs if m.tipo == "INGRESO"
        ) or Decimal("0")

        total_egresos = sum(
            m.monto for m in qs if m.tipo == "EGRESO"
        ) or Decimal("0")

        return {
            "periodo": f"{MESES_ES.get(int(mes), mes)} {anio}",
            "total_ingresos": float(total_ingresos),
            "total_egresos": float(total_egresos),
            "balance": float(total_ingresos - total_egresos),
            "cantidad_movimientos": qs.count(),
        }

    # -------------------------------------------------------------------------
    # Herramienta obtener_gastos_por_categoria
    # -------------------------------------------------------------------------

    def _obtener_gastos_por_categoria(self, anio: int, mes: int = None) -> dict:
        """
        Agrupa egresos por categoría y los suma. Útil para ver en qué se gasta más.
        """
        qs = Movimiento.objects.filter(
            usuario=self.usuario,
            activo=True,
            tipo="EGRESO",
            fecha_registro__year=int(anio),
        ).select_related("categoria")

        if mes:
            qs = qs.filter(fecha_registro__month=int(mes))

        # Agrupar manualmente (compatible con cualquier DB)
        agrupado = {}
        for m in qs:
            cat = m.categoria.nombre if m.categoria else "Sin categoría"
            agrupado[cat] = agrupado.get(cat, Decimal("0")) + m.monto

        # Ordenar de mayor a menor
        categorias = sorted(
            [{"categoria": cat, "total": float(total)} for cat, total in agrupado.items()],
            key=lambda x: x["total"],
            reverse=True,
        )

        periodo = f"{MESES_ES.get(int(mes), mes)} {anio}" if mes else str(anio)

        return {
            "periodo": periodo,
            "total_egresos": sum(c["total"] for c in categorias),
            "desglose_por_categoria": categorias,
        }