"""Ejecutor de herramientas que el LLM puede invocar (solo lectura)."""

import json
import logging
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum

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
        """Ingresos, egresos y balance de un mes/año usando Sum directo en DB."""
        aggs = Movimiento.objects.filter(
            usuario=self.usuario, activo=True,
            fecha_registro__month=int(mes),
            fecha_registro__year=int(anio),
        ).aggregate(
            total_ingresos=Sum('monto', filter=Q(tipo='INGRESO')),
            total_egresos=Sum('monto', filter=Q(tipo='EGRESO')),
            cantidad_movimientos=Sum(1),
        )
        ti = float(aggs['total_ingresos'] or Decimal('0'))
        te = float(aggs['total_egresos'] or Decimal('0'))
        return {
            "periodo": f"{MESES_ES.get(int(mes), mes)} {anio}",
            "total_ingresos": ti,
            "total_egresos": te,
            "balance": round(ti - te, 2),
            "cantidad_movimientos": aggs['cantidad_movimientos'] or 0,
        }

    # -------------------------------------------------------------------------
    # Herramienta obtener_gastos_por_categoria
    # -------------------------------------------------------------------------

    def _obtener_gastos_por_categoria(self, anio: int, mes: int = None) -> dict:
        """Egresos agrupados por categoría usando values().annotate(Sum) en DB."""
        qs = Movimiento.objects.filter(
            usuario=self.usuario, activo=True, tipo="EGRESO",
            fecha_registro__year=int(anio),
        )

        if mes:
            qs = qs.filter(fecha_registro__month=int(mes))

        agrupado = (
            qs.values('categoria__nombre')
            .annotate(total=Sum('monto'))
            .order_by('-total')
        )

        categorias = [
            {"categoria": item['categoria__nombre'] or "Sin categoría", "total": float(item['total'])}
            for item in agrupado
        ]

        periodo = f"{MESES_ES.get(int(mes), mes)} {anio}" if mes else str(anio)

        return {
            "periodo": periodo,
            "total_egresos": sum(c["total"] for c in categorias),
            "desglose_por_categoria": categorias,
        }