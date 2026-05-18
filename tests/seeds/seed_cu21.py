import os
import sys
import django

# Setup django environment
sys.path.append(r'c:\Users\Usuario\Downloads\GastuDjango')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gastu_django.settings')
django.setup()

from categorias.models import Categoria
from movimientos.models import Movimiento
from django.contrib.auth import get_user_model

def seed():
    print("Iniciando semillero para CU-21...")
    
    # 1. Asegurar categorías
    cat_salario, created = Categoria.objects.get_or_create(
        nombre='Salario',
        tipo='INGRESO',
        defaults={'descripcion': 'Salario mensual', 'activo': True}
    )
    if not created:
        cat_salario.activo = True
        cat_salario.save()

    cat_tecnologia, created = Categoria.objects.get_or_create(
        nombre='Tecnología',
        tipo='EGRESO',
        defaults={'descripcion': 'Gasto tecnológico', 'activo': True}
    )
    if not created:
        cat_tecnologia.activo = True
        cat_tecnologia.save()

    cat_alquileres, created = Categoria.objects.get_or_create(
        nombre='Alquileres',
        tipo='EGRESO',
        defaults={'descripcion': 'Gastos de alquiler', 'activo': True}
    )
    if not created:
        cat_alquileres.activo = True
        cat_alquileres.save()

    # 2. Encontrar usuario p@p.com
    User = get_user_model()
    try:
        u = User.objects.get(email='p@p.com')
    except User.DoesNotExist:
        print("Error: Usuario p@p.com no encontrado.")
        return

    # 3. Eliminar movimientos viejos de prueba para limpiar
    Movimiento.objects.filter(descripcion='Pago quincenal', usuario=u).delete()
    Movimiento.objects.filter(descripcion='Suscripción mensual', usuario=u).delete()

    # 4. Crear movimiento de ingreso "Pago quincenal"
    Movimiento.objects.create(
        descripcion='Pago quincenal',
        tipo='INGRESO',
        monto=1500000,
        categoria=cat_salario,
        usuario=u
    )
    print("Movimiento de ingreso 'Pago quincenal' creado.")

    # 5. Crear movimiento de egreso "Suscripción mensual"
    Movimiento.objects.create(
        descripcion='Suscripción mensual',
        tipo='EGRESO',
        monto=15000,
        categoria=cat_tecnologia,
        usuario=u
    )
    print("Movimiento de egreso 'Suscripción mensual' creado.")
        
    print("Semillero CU-21 completado con éxito.")

if __name__ == '__main__':
    seed()
