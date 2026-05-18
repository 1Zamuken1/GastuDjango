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
    print("Iniciando semillero para CU-22...")
    
    # 1. Asegurar categorías
    cat_salario, created = Categoria.objects.get_or_create(
        nombre='Salario',
        tipo='INGRESO',
        defaults={'descripcion': 'Salario mensual', 'activo': True}
    )
    if not created:
        cat_salario.activo = True
        cat_salario.save()

    cat_alimentacion, created = Categoria.objects.get_or_create(
        nombre='Alimentación',
        tipo='EGRESO',
        defaults={'descripcion': 'Mercado y comida', 'activo': True}
    )
    if not created:
        cat_alimentacion.activo = True
        cat_alimentacion.save()

    # 2. Encontrar usuario p@p.com
    User = get_user_model()
    try:
        u = User.objects.get(email='p@p.com')
    except User.DoesNotExist:
        print("Error: Usuario p@p.com no encontrado.")
        return

    # 3. Eliminar movimientos viejos de prueba para limpiar
    Movimiento.objects.filter(descripcion='Pago quincenal', usuario=u).delete()
    Movimiento.objects.filter(descripcion='Compra supermercado', usuario=u).delete()

    # 4. Crear movimiento de ingreso "Pago quincenal"
    Movimiento.objects.create(
        descripcion='Pago quincenal',
        tipo='INGRESO',
        monto=1500000,
        categoria=cat_salario,
        usuario=u
    )
    print("Movimiento de ingreso 'Pago quincenal' creado.")

    # 5. Crear movimiento de egreso "Compra supermercado"
    Movimiento.objects.create(
        descripcion='Compra supermercado',
        tipo='EGRESO',
        monto=75000,
        categoria=cat_alimentacion,
        usuario=u
    )
    print("Movimiento de egreso 'Compra supermercado' creado.")
        
    print("Semillero CU-22 completado con éxito.")

if __name__ == '__main__':
    seed()
