import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gastu_django.settings')
django.setup()

from django.utils import timezone
from usuarios.models import Usuario
from categorias.models import Categoria
from ahorros.models import AhorroMeta, AporteAhorro

usuario = Usuario.objects.filter(email='vale@gmail.com').first()
if not usuario:
    usuario = Usuario.objects.first()

cat = Categoria.objects.filter(tipo='EGRESO').first()

ahorro = AhorroMeta.objects.create(
    usuario=usuario,
    categoria=cat,
    descripcion="Ahorro Test Notificaciones",
    monto_meta=5000,
    frecuencia=AhorroMeta.Frecuencia.MENSUAL,
    fecha_meta=timezone.now().date() + timezone.timedelta(days=30),
    cantidad_cuotas=1
)

aporte = AporteAhorro.objects.create(
    ahorro=ahorro,
    aporte_asignado=5000,
    estado_ap=AporteAhorro.EstadoAp.PENDIENTE,
    fecha_limite=timezone.now().date() + timezone.timedelta(days=2)
)

print(f"Creado aporte {aporte.id} que vence en 2 días para {usuario.email}")
