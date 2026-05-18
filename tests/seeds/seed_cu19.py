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
    print("Iniciando semillero para CU-19...")
    
    # 1. Asegurar categorías
    cat_freelance, created = Categoria.objects.get_or_create(
        nombre='Freelance',
        tipo='INGRESO',
        defaults={'descripcion': 'Trabajos independientes', 'activo': True}
    )
    if created:
        print("Categoría 'Freelance' creada.")
    else:
        # Asegurarse de que esté activa
        cat_freelance.activo = True
        cat_freelance.save()

    cat_internet, created = Categoria.objects.get_or_create(
        nombre='Internet',
        tipo='EGRESO',
        defaults={'descripcion': 'Servicios de internet', 'activo': True}
    )
    if created:
        print("Categoría 'Internet' creada.")
    else:
        cat_internet.activo = True
        cat_internet.save()

    cat_servicios, created = Categoria.objects.get_or_create(
        nombre='Servicios Públicos',
        tipo='EGRESO',
        defaults={'descripcion': 'Luz, agua y gas', 'activo': True}
    )
    if created:
        print("Categoría 'Servicios Públicos' creada.")
    else:
        cat_servicios.activo = True
        cat_servicios.save()

    # 2. Encontrar usuario p@p.com
    User = get_user_model()
    try:
        u = User.objects.get(email='p@p.com')
    except User.DoesNotExist:
        print("Error: Usuario p@p.com no encontrado.")
        return

    # 3. Eliminar movimientos viejos de prueba para limpiar
    Movimiento.objects.filter(descripcion='Plan de internet mensual', usuario=u).delete()

    # 4. Crear movimiento de egreso bajo 'Internet'
    mov, created = Movimiento.objects.get_or_create(
        descripcion='Plan de internet mensual',
        tipo='EGRESO',
        monto=85000,
        categoria=cat_internet,
        usuario=u
    )
    if created:
        print("Movimiento de egreso 'Plan de internet mensual' creado bajo 'Internet'.")
        
    print("Semillero completado exitosamente.")

if __name__ == '__main__':
    seed()
