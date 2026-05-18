import os
import sys
import django

# Setup django environment
sys.path.append(r'c:\Users\Usuario\Downloads\GastuDjango')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gastu_django.settings')
django.setup()

from notificaciones.models import Notificacion
from django.contrib.auth import get_user_model

def seed():
    print("Iniciando semillero para CU-46...")
    
    # 1. Encontrar usuario p@p.com
    User = get_user_model()
    try:
        u = User.objects.get(email='p@p.com')
    except User.DoesNotExist:
        print("Error: Usuario p@p.com no encontrado.")
        return

    # 2. Eliminar notificaciones previas
    Notificacion.objects.filter(usuario=u).delete()
    print("Notificaciones previas eliminadas.")

    # 3. Crear 3 notificaciones no leídas de prueba
    Notificacion.objects.create(
        usuario=u,
        tipo=Notificacion.Tipo.DEFICIT,
        titulo="Balance en déficit",
        descripcion="Tu balance del mes actual está en déficit por $50,000.",
        modulo=Notificacion.Modulo.GENERAL,
        leida=False
    )
    Notificacion.objects.create(
        usuario=u,
        tipo=Notificacion.Tipo.EGRESO_GRANDE,
        titulo="Egreso grande registrado",
        descripcion="Registraste un egreso por $75,000 que supera el umbral.",
        modulo=Notificacion.Modulo.EGRESOS,
        leida=False
    )
    Notificacion.objects.create(
        usuario=u,
        tipo=Notificacion.Tipo.UMBRAL_MENSUAL,
        titulo="Umbral mensual alcanzado",
        descripcion="Has gastado el 90% de tu presupuesto de Alimentación.",
        modulo=Notificacion.Modulo.PRESUPUESTOS,
        leida=False
    )
    print("3 notificaciones no leídas creadas con éxito.")
    print("Semillero CU-46 completado.")

if __name__ == '__main__':
    seed()
