import calendar
from datetime import timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from django.db.models import OuterRef, Subquery, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone

from movimientos.models import Movimiento
from .models import Presupuesto


def _qs_con_total_gastado(qs):
    """Annota cada presupuesto con el total gastado en su rango de fechas en 1 subquery.

    Usa un Subquery correlacionado para evitar N+1 al calcular el gasto
    de múltiples presupuestos a la vez. El valor queda disponible como
    `presupuesto._total_gastado`.
    """
    return qs.select_related('categoria').annotate(
        _total_gastado=Coalesce(
            Subquery(
                Movimiento.objects.filter(
                    usuario=OuterRef('usuario'),
                    categoria=OuterRef('categoria'),
                    tipo='EGRESO',
                    activo=True,
                    fecha_registro__date__gte=OuterRef('fecha_inicio'),
                    fecha_registro__date__lte=OuterRef('fecha_fin'),
                ).values('categoria').annotate(
                    total=Sum('monto')
                ).values('total')[:1],
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
    )


def desactivar_presupuestos_vencidos(usuario):
    """Desactiva todos los presupuestos cuya fecha_fin ya pasó. Retorna los desactivados."""
    hoy = timezone.localdate()
    vencidos = Presupuesto.objects.filter(
        usuario=usuario,
        is_activo=True,
        fecha_fin__lt=hoy
    )
    desactivados = list(vencidos.values('id', 'fecha_fin', 'categoria__nombre'))
    vencidos.update(is_activo=False)
    return desactivados


def calcular_alerta_presupuesto(presupuesto):
    """Calcula el total gastado y porcentaje respecto al límite para un presupuesto.

    Si el presupuesto ya tiene el atributo ``_total_gastado`` (ej: vía
    ``_qs_con_total_gastado``) lo reusa; de lo contrario hace una consulta SUM.
    """
    total_gastado = getattr(presupuesto, '_total_gastado', None)
    if total_gastado is None:
        total_gastado = Movimiento.objects.filter(
            usuario=presupuesto.usuario,
            categoria=presupuesto.categoria,
            tipo='EGRESO',
            activo=True,
            fecha_registro__date__range=(
                presupuesto.fecha_inicio,
                presupuesto.fecha_fin
            )
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    limite = presupuesto.limite
    porcentaje = (total_gastado / limite) * 100 if limite > 0 else 0
    return total_gastado, porcentaje


def nivel_alerta(porcentaje):
    """Clasifica un porcentaje de consumo en un nivel de alerta textual.

    Los niveles van desde ``baja`` (< 50 %), pasando por ``nivel_50`` …
    ``nivel_95`` (cada 5 %), hasta ``critica`` (>= 100 %).
    """
    if porcentaje >= 100:
        return "critica"
    if porcentaje >= 50:
        return f"nivel_{(int(porcentaje) // 5) * 5}"
    return "baja"


def ritmo_presupuesto(presupuesto, disponible, hoy=None):
    """Calcula los dias que quedan del periodo y cuanto se puede gastar por dia.

    Retorna ``(dias_restantes, gasto_diario)``. Si el periodo ya termino o
    no ha empezado, ``gasto_diario`` es None.
    """
    hoy = hoy or timezone.localdate()
    if hoy > presupuesto.fecha_fin:
        return 0, None
    desde = max(hoy, presupuesto.fecha_inicio)
    dias = (presupuesto.fecha_fin - desde).days + 1
    if hoy < presupuesto.fecha_inicio or dias <= 0:
        return dias, None
    gasto_diario = max(Decimal(disponible), Decimal('0')) / dias
    return dias, gasto_diario


def obtener_estado_presupuesto(presupuesto):
    """Arma el dict de estado completo (gastado, porcentaje, alerta) para un presupuesto."""
    total_gastado, porcentaje = calcular_alerta_presupuesto(presupuesto)
    alerta = nivel_alerta(porcentaje)
    disponible = presupuesto.limite - total_gastado
    dias_restantes, gasto_diario = ritmo_presupuesto(presupuesto, disponible)
    return {
        "id": presupuesto.id,
        "categoria": presupuesto.categoria.nombre,
        "categoria_id": presupuesto.categoria.id,
        "limite": float(presupuesto.limite),
        "gastado": float(total_gastado),
        "disponible": float(presupuesto.limite - total_gastado),
        "porcentaje": round(float(porcentaje), 2),
        "alerta": alerta,
        "dias_restantes": dias_restantes,
        "gasto_diario": round(float(gasto_diario)) if gasto_diario is not None else None,
    }


def obtener_estados_presupuestos(usuario, solo_activos=True):
    """Retorna los presupuestos con su alerta en 1 sola consulta SQL."""
    qs = Presupuesto.objects.filter(usuario=usuario)
    if solo_activos:
        qs = qs.filter(is_activo=True)
    presupuestos = _qs_con_total_gastado(qs)
    return [obtener_estado_presupuesto(p) for p in presupuestos]

def _es_mes_calendario(inicio, fin):
    """True si el periodo cubre meses completos (del dia 1 al ultimo dia de un mes)."""
    ultimo = calendar.monthrange(fin.year, fin.month)[1]
    return inicio.day == 1 and fin.day == ultimo


def periodo_siguiente(inicio, fin, hoy=None):
    """Calcula el periodo que sigue a ``inicio``-``fin`` y que todavia esta vigente.

    Los periodos de meses completos avanzan por meses (abril -> mayo);
    los demas avanzan por la misma cantidad de dias. Si el usuario renueva
    tarde, se saltan los periodos que ya terminaron.
    """
    hoy = hoy or timezone.localdate()
    if _es_mes_calendario(inicio, fin):
        meses = (fin.year - inicio.year) * 12 + (fin.month - inicio.month) + 1
        nuevo_inicio = inicio + relativedelta(months=meses)
        nuevo_fin = nuevo_inicio + relativedelta(months=meses) - timedelta(days=1)
        while nuevo_fin < hoy:
            nuevo_inicio += relativedelta(months=meses)
            nuevo_fin = nuevo_inicio + relativedelta(months=meses) - timedelta(days=1)
        return nuevo_inicio, nuevo_fin

    duracion = (fin - inicio).days + 1
    nuevo_inicio = fin + timedelta(days=1)
    while nuevo_inicio + timedelta(days=duracion - 1) < hoy:
        nuevo_inicio += timedelta(days=duracion)
    return nuevo_inicio, nuevo_inicio + timedelta(days=duracion - 1)


class RenovacionError(Exception):
    """El presupuesto no se puede renovar; el mensaje es apto para el usuario."""


def renovar_presupuesto(presupuesto, hoy=None):
    """Crea el presupuesto del periodo siguiente con la misma categoria y limite.

    Solo se renuevan presupuestos inactivos o vencidos, y siempre que la
    categoria no tenga ya otro presupuesto activo. El original queda inactivo.
    """
    hoy = hoy or timezone.localdate()
    if presupuesto.is_activo and presupuesto.fecha_fin >= hoy:
        raise RenovacionError("Este presupuesto sigue vigente. Podrás renovarlo cuando termine.")

    otro_activo = Presupuesto.objects.filter(
        usuario=presupuesto.usuario, categoria=presupuesto.categoria, is_activo=True
    ).exclude(pk=presupuesto.pk).exists()
    if otro_activo:
        raise RenovacionError("Ya tienes un presupuesto activo para esta categoría.")

    inicio, fin = periodo_siguiente(presupuesto.fecha_inicio, presupuesto.fecha_fin, hoy)
    if presupuesto.is_activo:
        presupuesto.is_activo = False
        presupuesto.save(update_fields=['is_activo'])

    return Presupuesto.objects.create(
        usuario=presupuesto.usuario,
        categoria=presupuesto.categoria,
        limite=presupuesto.limite,
        fecha_inicio=inicio,
        fecha_fin=fin,
        is_activo=True,
    )
