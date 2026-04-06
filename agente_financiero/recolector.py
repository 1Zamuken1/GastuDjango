"""
agente_financiero/recolector.py

Recolecta todos los datos del usuario autenticado desde el ORM de Django.
SOLO LECTURA — nunca crea, edita ni elimina registros.
Todos los queries SIEMPRE filtran por usuario para aislar datos.
"""

from datetime import date
from decimal import Decimal

from movimientos.models import Movimiento
from ahorros.models import AhorroMeta, AporteAhorro
from presupuesto.models import Presupuesto
from programaciones.models import Programacion

# Importa ResumenMensual desde la app dashboard si existe
try:
    from dashboard.models import ResumenMensual
    TIENE_RESUMEN_MENSUAL = True
except ImportError:
    TIENE_RESUMEN_MENSUAL = False


class RecolectorDatos:
    """
    Clase que recolecta toda la información financiera del usuario
    haciendo queries directas al ORM (sin pasar por HTTP).

    Uso:
        recolector = RecolectorDatos(request.user)
        datos = recolector.recolectar_todo()
    """

    def __init__(self, usuario):
        self.usuario = usuario
        self.hoy = date.today()
        self.mes_actual = self.hoy.month
        self.anio_actual = self.hoy.year

    def recolectar_todo(self) -> dict:
        """
        Punto de entrada principal.
        Retorna un dict con todos los datos del usuario listos para el prompt.
        """
        return {
            "usuario": self._datos_usuario(),
            "resumen_mensual": self._resumen_mensual(),
            "ultimos_movimientos": self._ultimos_movimientos(),
            "metas_ahorro": self._metas_ahorro(),
            "presupuestos": self._presupuestos_activos(),
            "programaciones": self._programaciones_activas(),
            "mes": self.mes_actual,
            "anio": self.anio_actual,
        }

    # -------------------------------------------------------------------------
    # Datos del usuario
    # -------------------------------------------------------------------------

    def _datos_usuario(self) -> dict:
        return {
            "nombre": self.usuario.get_full_name() or self.usuario.username,
            "email": self.usuario.email,
        }

    # -------------------------------------------------------------------------
    # Resumen mensual
    # -------------------------------------------------------------------------

    def _resumen_mensual(self) -> dict:
        """
        Intenta leer ResumenMensual si existe.
        Si no existe el modelo, calcula el resumen directamente desde Movimiento.
        """
        if TIENE_RESUMEN_MENSUAL:
            try:
                resumen = ResumenMensual.objects.get(
                    usuario=self.usuario,
                    mes=self.mes_actual,
                    anio=self.anio_actual,
                )
                return {
                    "total_ingresos": float(resumen.total_ingresos),
                    "total_egresos": float(resumen.total_egresos),
                    "disponible": float(resumen.disponible),
                    "total_ahorrado": float(getattr(resumen, "total_ahorrado", 0)),
                }
            except ResumenMensual.DoesNotExist:
                pass  # Calcula manualmente si no hay registro

        # Cálculo manual desde Movimiento
        movimientos_mes = Movimiento.objects.filter(
            usuario=self.usuario,
            fecha_registro__month=self.mes_actual,
            fecha_registro__year=self.anio_actual,
            activo=True,
        )

        total_ingresos = sum(
            m.monto for m in movimientos_mes if m.tipo == "INGRESO"
        ) or Decimal("0")

        total_egresos = sum(
            m.monto for m in movimientos_mes if m.tipo == "EGRESO"
        ) or Decimal("0")

        return {
            "total_ingresos": float(total_ingresos),
            "total_egresos": float(total_egresos),
            "disponible": float(total_ingresos - total_egresos),
            "total_ahorrado": 0,  # No calculado si no hay ResumenMensual
        }

    # -------------------------------------------------------------------------
    # Últimos movimientos
    # -------------------------------------------------------------------------

    def _ultimos_movimientos(self, cantidad: int = 10) -> list:
        movimientos = (
            Movimiento.objects.filter(usuario=self.usuario, activo=True)
            .select_related("categoria")
            .order_by("-fecha_registro")[:cantidad]
        )

        return [
            {
                "fecha": m.fecha_registro.strftime("%d/%m/%Y"),
                "tipo": m.tipo,
                "monto": float(m.monto),
                "categoria": m.categoria.nombre if m.categoria else "Sin categoría",
                "descripcion": m.descripcion or "",
            }
            for m in movimientos
        ]

    # -------------------------------------------------------------------------
    # Metas de ahorro
    # -------------------------------------------------------------------------

    def _metas_ahorro(self) -> list:
        metas = (
            AhorroMeta.objects.filter(
                usuario=self.usuario,
                estado__in=["ACTIVO", "SIN_INICIAR"],
            )
            .select_related("categoria")
            .order_by("fecha_meta")
        )

        resultado = []
        for meta in metas:
            cuotas_pendientes = AporteAhorro.objects.filter(
                ahorro=meta, estado_ap="PENDIENTE"
            ).count()

            resultado.append({
                "categoria": meta.categoria.nombre if meta.categoria else "Sin categoría",
                "descripcion": meta.descripcion or "",
                "monto_meta": float(meta.monto_meta),
                "total_acumulado": float(meta.total_acumulado),
                "porcentaje": round(
                    (float(meta.total_acumulado) / float(meta.monto_meta) * 100), 1
                ) if meta.monto_meta else 0,
                "fecha_meta": meta.fecha_meta.strftime("%d/%m/%Y"),
                "estado": meta.estado,
                "frecuencia": meta.frecuencia,
                "cuotas_pendientes": cuotas_pendientes,
            })

        return resultado

    # -------------------------------------------------------------------------
    # Presupuestos activos
    # -------------------------------------------------------------------------

    def _presupuestos_activos(self) -> list:
        # Intenta con isActivo o activo según el modelo
        try:
            presupuestos = Presupuesto.objects.filter(
                usuario=self.usuario, isActivo=True
            ).select_related("categoria")
        except Exception:
            presupuestos = Presupuesto.objects.filter(
                usuario=self.usuario, activo=True
            ).select_related("categoria")

        resultado = []
        for p in presupuestos:
            limite = float(p.monto_limite) if hasattr(p, "monto_limite") else float(getattr(p, "limite", 0))
            gastado = float(p.monto_gastado) if hasattr(p, "monto_gastado") else 0
            porcentaje = round((gastado / limite * 100), 1) if limite else 0

            resultado.append({
                "categoria": p.categoria.nombre if p.categoria else "Sin categoría",
                "limite": limite,
                "gastado": gastado,
                "disponible": round(limite - gastado, 2),
                "porcentaje_usado": porcentaje,
                "alerta": porcentaje >= 80,  # Alerta si superó el 80%
            })

        return resultado

    # -------------------------------------------------------------------------
    # Programaciones activas
    # -------------------------------------------------------------------------

    def _programaciones_activas(self) -> list:
        try:
            programaciones = Programacion.objects.filter(
                usuario=self.usuario, activo=True
            ).select_related("categoria")
        except Exception:
            return []

        return [
            {
                "categoria": p.categoria.nombre if p.categoria else "Sin categoría",
                "monto": float(p.monto_programado),
                "frecuencia": getattr(p, "frecuencia", ""),
                "proxima_fecha": (
                    p.proxima_ejecucion.strftime("%d/%m/%Y")
                    if hasattr(p, "proxima_fecha") and p.proxima_fecha
                    else "No definida"
                ),
                "descripcion": getattr(p, "descripcion", "") or "",
            }
            for p in programaciones
        ]