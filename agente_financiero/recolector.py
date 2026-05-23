"""Recolecta datos financieros del usuario desde el ORM (solo lectura)."""

from datetime import date
from decimal import Decimal

from django.db.models import DecimalField, IntegerField, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce

from movimientos.models import Movimiento
from ahorros.models import AhorroMeta, AporteAhorro
from presupuesto.models import Presupuesto
from programaciones.models import Programacion

try:
    from dashboard.models import ResumenMensual
    TIENE_RESUMEN_MENSUAL = True
except ImportError:
    TIENE_RESUMEN_MENSUAL = False


class RecolectorDatos:
    """Recolecta toda la información financiera del usuario para enviar al prompt del LLM."""

    def __init__(self, usuario):
        self.usuario = usuario
        self.hoy = date.today()
        self.mes_actual = self.hoy.month
        self.anio_actual = self.hoy.year

    def recolectar_todo(self) -> dict:
        """Dict completo con datos del usuario, resumen, movimientos, metas, presupuestos y programaciones."""
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

    def _datos_usuario(self) -> dict:
        return {
            "nombre": self.usuario.get_full_name() or self.usuario.username,
            "email": self.usuario.email,
        }

    def _resumen_mensual(self) -> dict:
        """Resumen del mes desde ResumenMensual o calculado con SUM directo en DB."""
        if TIENE_RESUMEN_MENSUAL:
            try:
                resumen = ResumenMensual.objects.get(
                    usuario=self.usuario, mes=self.mes_actual, anio=self.anio_actual,
                )
                return {
                    "total_ingresos": float(resumen.total_ingresos),
                    "total_egresos": float(resumen.total_egresos),
                    "disponible": float(resumen.disponible),
                    "total_ahorrado": float(getattr(resumen, "total_ahorrado", 0)),
                }
            except ResumenMensual.DoesNotExist:
                pass

        aggs = Movimiento.objects.filter(
            usuario=self.usuario, activo=True,
            fecha_registro__month=self.mes_actual,
            fecha_registro__year=self.anio_actual,
        ).aggregate(
            total_ingresos=Coalesce(Sum('monto', filter=Q(tipo='INGRESO')), Decimal('0')),
            total_egresos=Coalesce(Sum('monto', filter=Q(tipo='EGRESO')), Decimal('0')),
        )
        ti, te = float(aggs['total_ingresos']), float(aggs['total_egresos'])
        return {
            "total_ingresos": ti,
            "total_egresos": te,
            "disponible": round(ti - te, 2),
            "total_ahorrado": 0,
        }

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

    def _metas_ahorro(self) -> list:
        """Metas activas del usuario. Las cuotas pendientes se anotan en 1 subquery."""
        metas = (
            AhorroMeta.objects.filter(
                usuario=self.usuario, estado__in=["ACTIVO", "SIN_INICIAR"],
            )
            .select_related("categoria")
        .annotate(
            _cuotas_pendientes=Coalesce(
                Subquery(
                    AporteAhorro.objects.filter(
                        ahorro=OuterRef('pk'), estado_ap="PENDIENTE",
                    ).values('ahorro').annotate(
                        total=Sum(1, output_field=IntegerField())
                    ).values('total')[:1],
                    output_field=IntegerField(),
                ),
                0,
            )
        )
            .order_by("fecha_meta")
        )

        return [
            {
                "categoria": m.categoria.nombre if m.categoria else "Sin categoría",
                "descripcion": m.descripcion or "",
                "monto_meta": float(m.monto_meta),
                "total_acumulado": float(m.total_acumulado),
                "porcentaje": round(float(m.total_acumulado) / float(m.monto_meta) * 100, 1)
                if m.monto_meta else 0,
                "fecha_meta": m.fecha_meta.strftime("%d/%m/%Y"),
                "estado": m.estado,
                "frecuencia": m.frecuencia,
                "cuotas_pendientes": m._cuotas_pendientes,
            }
            for m in metas
        ]

    def _presupuestos_activos(self) -> list:
        """Presupuestos activos del usuario. Calcula gastado desde Movimiento en 1 subquery."""
        presupuestos = (
            Presupuesto.objects.filter(usuario=self.usuario, isActivo=True)
            .select_related("categoria")
            .annotate(
                _gastado=Coalesce(
                    Subquery(
                        Movimiento.objects.filter(
                            usuario=OuterRef('usuario'),
                            categoria=OuterRef('categoria'),
                            tipo='EGRESO',
                            fecha_registro__date__gte=OuterRef('fecha_inicio'),
                            fecha_registro__date__lte=OuterRef('fecha_fin'),
                        ).values('categoria').annotate(
                            total=Sum('monto')
                        ).values('total')[:1],
                        output_field=DecimalField(),
                    ),
                    Decimal('0'),
                )
            )
        )

        resultado = []
        for p in presupuestos:
            limite = float(p.limite)
            gastado = float(p._gastado)
            disponible = round(limite - gastado, 2)
            porcentaje = round(gastado / limite * 100, 1) if limite else 0
            resultado.append({
                "categoria": p.categoria.nombre if p.categoria else "Sin categoría",
                "limite": limite,
                "gastado": gastado,
                "disponible": disponible,
                "porcentaje_usado": porcentaje,
                "alerta": porcentaje >= 80,
            })
        return resultado

    def _programaciones_activas(self) -> list:
        """Programaciones activas del usuario con su próxima fecha de ejecución."""
        programaciones = (
            Programacion.objects.filter(usuario=self.usuario, activo=True)
            .select_related("categoria")
        )
        return [
            {
                "categoria": p.categoria.nombre if p.categoria else "Sin categoría",
                "monto": float(p.monto_programado),
                "frecuencia": p.frecuencia,
                "proxima_fecha": (
                    p.proxima_ejecucion.strftime("%d/%m/%Y")
                    if p.proxima_ejecucion else "No definida"
                ),
                "descripcion": p.descripcion or "",
            }
            for p in programaciones
        ]