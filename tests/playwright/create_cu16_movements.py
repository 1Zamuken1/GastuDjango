import os
import django
from decimal import Decimal
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gastu_django.settings')
django.setup()

from django.contrib.auth import get_user_model
from movimientos.models import Movimiento
from categorias.models import Categoria
from django.utils import timezone

User = get_user_model()

def create_movements():
    user = User.objects.get(email='p@p.com')
    
    # Clean up existing movements for p@p.com to have a clean state
    Movimiento.objects.filter(usuario=user).delete()
    print("Deleted old movements.")
    
    # Get categories
    cat_salario = Categoria.objects.get(id=1)
    cat_vivienda = Categoria.objects.get(id=11)
    cat_alimentacion = Categoria.objects.get(id=12)
    
    # ── Create April 2026 movements (for historical export tests)
    m1 = Movimiento.objects.create(
        usuario=user,
        tipo='INGRESO',
        categoria=cat_salario,
        descripcion='Sueldo Abril 2026',
        monto=Decimal('3500.00'),
        activo=True
    )
    Movimiento.objects.filter(pk=m1.pk).update(fecha_registro=timezone.make_aware(datetime.datetime(2026, 4, 10, 10, 0)))
    
    m2 = Movimiento.objects.create(
        usuario=user,
        tipo='EGRESO',
        categoria=cat_vivienda,
        descripcion='Alquiler de Abril',
        monto=Decimal('1200.00'),
        activo=True
    )
    Movimiento.objects.filter(pk=m2.pk).update(fecha_registro=timezone.make_aware(datetime.datetime(2026, 4, 5, 12, 0)))

    m3 = Movimiento.objects.create(
        usuario=user,
        tipo='EGRESO',
        categoria=cat_alimentacion,
        descripcion='Supermercado Semanal',
        monto=Decimal('350.00'),
        activo=True
    )
    Movimiento.objects.filter(pk=m3.pk).update(fecha_registro=timezone.make_aware(datetime.datetime(2026, 4, 15, 18, 0)))
    
    # ── Create May 2026 movements (for current month display & cards list in UI)
    m_may_1 = Movimiento.objects.create(
        usuario=user,
        tipo='INGRESO',
        categoria=cat_salario,
        descripcion='Sueldo Mayo 2026',
        monto=Decimal('4000.00'),
        activo=True
    )
    Movimiento.objects.filter(pk=m_may_1.pk).update(fecha_registro=timezone.make_aware(datetime.datetime(2026, 5, 10, 10, 0)))

    m_may_2 = Movimiento.objects.create(
        usuario=user,
        tipo='EGRESO',
        categoria=cat_vivienda,
        descripcion='Alquiler de Mayo',
        monto=Decimal('1250.00'),
        activo=True
    )
    Movimiento.objects.filter(pk=m_may_2.pk).update(fecha_registro=timezone.make_aware(datetime.datetime(2026, 5, 5, 12, 0)))

    m_may_3 = Movimiento.objects.create(
        usuario=user,
        tipo='EGRESO',
        categoria=cat_alimentacion,
        descripcion='Supermercado Mayo',
        monto=Decimal('420.00'),
        activo=True
    )
    Movimiento.objects.filter(pk=m_may_3.pk).update(fecha_registro=timezone.make_aware(datetime.datetime(2026, 5, 12, 15, 0)))

    print("Created movements for April 2026 & May 2026 successfully.")

if __name__ == '__main__':
    create_movements()
