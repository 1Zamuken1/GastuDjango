from decimal import Decimal
from django.db.models import Sum

def total_en_rango(usuario, tipo, inicio, fin):
    """Suma de montos de movimientos del usuario en un rango de fechas."""
    from movimientos.models import Movimiento

    resultado = Movimiento.objects.filter(
        usuario=usuario,
        tipo=tipo,
        fecha_registro__range=(inicio, fin),
    ).aggregate(total=Sum('monto'))['total']
    
    if resultado is None:
        return Decimal('0')
    return Decimal(str(resultado))


def count_en_rango(usuario, tipo, inicio, fin):
    """Cantidad de movimientos del usuario en un rango de fechas."""
    from movimientos.models import Movimiento

    return Movimiento.objects.filter(
        usuario=usuario,
        tipo=tipo,
        fecha_registro__range=(inicio, fin),
    ).count()


def fin_mes(dt):
    """Retorna el último instante del mes del datetime dado."""
    import calendar
    ultimo_dia = calendar.monthrange(dt.year, dt.month)[1]
    return dt.replace(day=ultimo_dia, hour=23, minute=59, second=59, microsecond=999999)
