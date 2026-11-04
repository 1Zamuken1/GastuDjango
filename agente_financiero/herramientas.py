"""Ejecutor de herramientas que el LLM puede invocar (solo lectura)."""

import json
import logging
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum, Count
from categorias.models import Categoria
from ahorros.models import AhorroMeta, AporteAhorro
from presupuesto.models import Presupuesto
from programaciones.models import Programacion

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
            'obtener_movimientos': self._obtener_movimientos,
            'obtener_resumen_periodo': self._obtener_resumen_periodo,
            'obtener_gastos_por_categoria': self._obtener_gastos_por_categoria,
            'calcular_proyeccion_meta': self._calcular_proyeccion_meta,
            'calcular_ritmo_gasto': self._calcular_ritmo_gasto,
            'calcular_capacidad_disponible': self._calcular_capacidad_disponible,
            'crear_movimiento': self._crear_movimiento,
            'obtener_estado_ahorros': self._obtener_estado_ahorros,
            'obtener_estado_presupuestos': self._obtener_estado_presupuestos,
            'preparar_confirmacion_accion': self._preparar_confirmacion_accion,
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
            cantidad_movimientos=Count('id'),
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
    # -------------------------------------------------------------------------
    # Herramientas Matemáticas Exactas (Python Determinista)
    # -------------------------------------------------------------------------

    def _calcular_proyeccion_meta(self, meta_id: int, aporte_adicional_mensual: float = 0.0) -> dict:
        """
        Calcula matemáticamente cuánto tiempo y cuotas restan para cumplir una meta de ahorro.
        """
        try:
            meta = AhorroMeta.objects.get(id=meta_id, usuario=self.usuario)
        except AhorroMeta.DoesNotExist:
            return {"error": f"Meta de ahorro con id {meta_id} no encontrada."}

        acumulado = meta.aportes.filter(estado_ap='APORTADO').aggregate(total=Sum('aporte'))['total'] or Decimal('0')
        restante = max(Decimal('0'), Decimal(str(meta.monto_meta)) - acumulado)
        cuotas_pendientes = meta.aportes.filter(estado_ap='PENDIENTE').count()
        valor_cuota = meta.monto_cuota or (restante / cuotas_pendientes if cuotas_pendientes else restante)

        proyeccion = {
            "meta_id": meta.id,
            "descripcion": meta.descripcion_corta or meta.categoria.nombre,
            "monto_meta": float(meta.monto_meta),
            "monto_acumulado": float(acumulado),
            "monto_restante": float(restante),
            "porcentaje_avance": round(float((acumulado / meta.monto_meta) * 100), 2) if meta.monto_meta else 0.0,
            "cuotas_pendientes": cuotas_pendientes,
            "valor_cuota_habitual": float(valor_cuota),
            "fecha_limite": meta.fecha_meta.strftime("%d/%m/%Y") if meta.fecha_meta else "Sin fecha",
        }

        if aporte_adicional_mensual > 0:
            aporte_total_estimado = valor_cuota + Decimal(str(aporte_adicional_mensual))
            cuotas_estimadas = int((restante / aporte_total_estimado).to_integral_value()) if aporte_total_estimado > 0 else 0
            proyeccion["con_aceleracion"] = {
                "aporte_mensual_propuesto": float(aporte_total_estimado),
                "cuotas_estimadas_restantes": max(1, cuotas_estimadas),
            }

        return proyeccion

    def _calcular_ritmo_gasto(self, categoria: str = None) -> dict:
        """
        Calcula el ritmo de gasto diario promedio y la proyección de cierre de mes.
        """
        hoy = self.hoy
        dia_actual = hoy.day
        # Total de días del mes actual
        import calendar
        dias_en_mes = calendar.monthrange(hoy.year, hoy.month)[1]
        dias_restantes = dias_en_mes - dia_actual

        qs = Movimiento.objects.filter(
            usuario=self.usuario, activo=True, tipo="EGRESO",
            fecha_registro__year=hoy.year, fecha_registro__month=hoy.month
        )

        cat_nombre = "Todas las categorías"
        if categoria:
            qs = qs.filter(categoria__nombre__icontains=categoria)
            cat_nombre = categoria

        total_gastado = qs.aggregate(total=Sum('monto'))['total'] or Decimal('0')
        gasto_diario_promedio = (total_gastado / Decimal(str(dia_actual))) if dia_actual > 0 else Decimal('0')
        proyeccion_fin_mes = total_gastado + (gasto_diario_promedio * Decimal(str(dias_restantes)))

        return {
            "categoria": cat_nombre,
            "dias_transcurridos": dia_actual,
            "dias_restantes_mes": dias_restantes,
            "total_gastado_a_la_fecha": float(total_gastado),
            "gasto_diario_promedio": round(float(gasto_diario_promedio), 2),
            "gasto_proyectado_fin_mes": round(float(proyeccion_fin_mes), 2),
        }

    def _calcular_capacidad_disponible(self) -> dict:
        """
        Calcula el disponible real del usuario descontando obligaciones mensuales fijas.
        """
        hoy = self.hoy
        resumen = Movimiento.objects.filter(
            usuario=self.usuario, activo=True,
            fecha_registro__year=hoy.year, fecha_registro__month=hoy.month
        ).aggregate(
            ingresos=Sum('monto', filter=Q(tipo='INGRESO')),
            egresos=Sum('monto', filter=Q(tipo='EGRESO')),
        )

        ingresos = resumen['ingresos'] or Decimal('0')
        egresos = resumen['egresos'] or Decimal('0')
        saldo_actual = ingresos - egresos

        # Obligaciones de ahorro pendientes este mes
        ahorros_pendientes = AporteAhorro.objects.filter(
            ahorro__usuario=self.usuario,
            estado_ap='PENDIENTE',
            fecha_limite__year=hoy.year,
            fecha_limite__month=hoy.month
        ).aggregate(total=Sum('aporte'))['total'] or Decimal('0')

        disponible_neto_libre = max(Decimal('0'), saldo_actual - ahorros_pendientes)

        return {
            "ingresos_mes": float(ingresos),
            "egresos_mes": float(egresos),
            "saldo_actual": float(saldo_actual),
            "compromisos_ahorro_pendientes": float(ahorros_pendientes),
            "disponible_libre_real": float(disponible_neto_libre),
        }

    # -------------------------------------------------------------------------
    # Herramientas de Escritura y Consultas Extendidas (CRUD)
    # -------------------------------------------------------------------------

    def _crear_movimiento(self, tipo: str, categoria: str, monto: float, descripcion: str = "") -> dict:
        """
        Crea un movimiento (INGRESO o EGRESO) en la base de datos para el usuario autenticado.
        """
        tipo = tipo.upper().strip()
        if tipo not in ["INGRESO", "EGRESO"]:
            return {"error": "El tipo debe ser 'INGRESO' o 'EGRESO'."}

        monto_dec = Decimal(str(monto))
        if monto_dec <= Decimal('0'):
            return {"error": "El monto debe ser mayor a 0."}

        # Buscar categoría más afín
        cat_obj = Categoria.objects.filter(
            nombre__icontains=categoria.strip(),
            tipo=tipo,
            activo=True
        ).first()

        if not cat_obj:
            # Fallback a cualquier categoría activa del tipo
            cat_obj = Categoria.objects.filter(tipo=tipo, activo=True).first()
            if not cat_obj:
                return {"error": f"No se encontró una categoría válida para el tipo {tipo}."}

        mov = Movimiento.objects.create(
            usuario=self.usuario,
            categoria=cat_obj,
            tipo=tipo,
            monto=monto_dec,
            descripcion=descripcion.strip() or f"Registrado vía asistente GASTU"
        )

        return {
            "ok": True,
            "id": mov.id,
            "tipo": mov.tipo,
            "categoria": mov.categoria.nombre,
            "monto": float(mov.monto),
            "descripcion": mov.descripcion,
            "fecha": mov.fecha_registro.strftime("%d/%m/%Y"),
            "mensaje": f"Se ha registrado exitosamente el {mov.tipo.lower()} por  en '{mov.categoria.nombre}'."
        }

    def _obtener_estado_ahorros(self) -> dict:
        """Retorna las metas de ahorro activas del usuario con su progreso exacto."""
        metas = AhorroMeta.objects.filter(usuario=self.usuario, activo=True).select_related('categoria')
        resultado = []
        for m in metas:
            acumulado = m.aportes.filter(estado_ap='APORTADO').aggregate(total=Sum('aporte'))['total'] or Decimal('0')
            pendientes = m.aportes.filter(estado_ap='PENDIENTE').count()
            resultado.append({
                "id": m.id,
                "categoria": m.categoria.nombre if m.categoria else "General",
                "descripcion": m.descripcion_corta or "",
                "monto_meta": float(m.monto_meta),
                "acumulado": float(acumulado),
                "cuotas_pendientes": pendientes,
                "estado": m.estado,
                "fecha_meta": m.fecha_meta.strftime("%d/%m/%Y") if m.fecha_meta else "Sin fecha",
            })
        return {"total_metas": len(resultado), "metas": resultado}

    def _obtener_estado_presupuestos(self) -> dict:
        """Retorna los presupuestos activos del usuario con lo gastado y disponible."""
        from presupuesto.services import obtener_estados_presupuestos
        presupuestos = obtener_estados_presupuestos(self.usuario, solo_activos=True)
        return {"total_presupuestos": len(presupuestos), "presupuestos": presupuestos}

    # -------------------------------------------------------------------------
    # Firewall de Confirmación (Human-in-the-Loop)
    # -------------------------------------------------------------------------

    def _preparar_confirmacion_accion(
        self,
        tipo_accion: str,
        referencia_id: int,
        detalles_modificacion: dict = None,
        motivo: str = ""
    ) -> dict:
        """
        Intercepta y valida peticiones de borrado o edición destructiva.
        Genera un payload seguro que el frontend interpreta para mostrar la tarjeta interactiva de confirmación.
        """
        tipo_accion = tipo_accion.upper().strip()

        if tipo_accion in ["ELIMINAR_MOVIMIENTO", "EDITAR_MOVIMIENTO"]:
            try:
                mov = Movimiento.objects.select_related("categoria").get(
                    id=referencia_id, usuario=self.usuario, activo=True
                )
            except Movimiento.DoesNotExist:
                return {
                    "ok": False,
                    "error": f"No se encontró un movimiento activo con ID {referencia_id} perteneciente a tu cuenta."
                }

            if tipo_accion == "ELIMINAR_MOVIMIENTO":
                return {
                    "requiere_confirmacion": True,
                    "tipo_accion": "ELIMINAR_MOVIMIENTO",
                    "objeto_id": mov.id,
                    "endpoint": f"/movimientos/api/eliminar/{mov.id}/",
                    "resumen_accion": f"Eliminar {mov.tipo.lower()} de ${float(mov.monto):,.0f} en '{mov.categoria.nombre}' ({mov.descripcion or 'Sin descripción'})",
                    "mensaje_al_usuario": f"He preparado la eliminación del {mov.tipo.lower()} por  en '{mov.categoria.nombre}'. Por favor confirma a continuación para procesarlo:"
                }

            elif tipo_accion == "EDITAR_MOVIMIENTO":
                detalles = detalles_modificacion or {}
                return {
                    "requiere_confirmacion": True,
                    "tipo_accion": "EDITAR_MOVIMIENTO",
                    "objeto_id": mov.id,
                    "endpoint": f"/movimientos/api/editar/{mov.id}/",
                    "detalles_modificacion": detalles,
                    "resumen_accion": f"Modificar movimiento ID {mov.id} (Valor actual: ${float(mov.monto):,.0f})",
                    "mensaje_al_usuario": f"He preparado los cambios para el movimiento en '{mov.categoria.nombre}'. Confirma para aplicarlos:"
                }

        elif tipo_accion == "ELIMINAR_PRESUPUESTO":
            try:
                pres = Presupuesto.objects.select_related("categoria").get(
                    id=referencia_id, usuario=self.usuario, is_activo=True
                )
            except Presupuesto.DoesNotExist:
                return {
                    "ok": False,
                    "error": f"No se encontró un presupuesto activo con ID {referencia_id} perteneciente a tu cuenta."
                }

            return {
                "requiere_confirmacion": True,
                "tipo_accion": "ELIMINAR_PRESUPUESTO",
                "objeto_id": pres.id,
                "endpoint": f"/api/presupuestos/{pres.id}/",
                "resumen_accion": f"Eliminar presupuesto de ${float(pres.limite):,.0f} para '{pres.categoria.nombre}'",
                "mensaje_al_usuario": f"He preparado la eliminación del presupuesto de '{pres.categoria.nombre}'. Confirma a continuación:"
            }

        return {
            "ok": False,
            "error": f"Tipo de acción '{tipo_accion}' no soportada por el firewall de seguridad."
        }