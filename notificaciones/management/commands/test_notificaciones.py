from django.core.management.base import BaseCommand
from django.utils import timezone
from movimientos.models import Movimiento
from categorias.models import Categoria
from usuarios.models import Usuario

class Command(BaseCommand):
    help = 'Genera datos de prueba para disparar notificaciones en la cuenta admin.'

    def handle(self, *args, **options):
        usuarios = Usuario.objects.all()
        if not usuarios.exists():
            self.stdout.write(self.style.ERROR('No hay usuarios en la base de datos.'))
            return
        
        from notificaciones.models import Notificacion
        cat_ingreso = Categoria.objects.filter(tipo='INGRESO').first()
        cat_egreso = Categoria.objects.filter(tipo='EGRESO').first()
        now = timezone.now()

        for usuario in usuarios:
            self.stdout.write(f"--- Generando datos para {usuario.email} ---")
            
            # Limpiar notificaciones previas
            Notificacion.objects.filter(usuario=usuario).delete()

            for i in range(1, 4):
                m = Movimiento.objects.create(
                    usuario=usuario, tipo='INGRESO', categoria=cat_ingreso,
                    monto=2000.00, descripcion=f'Salario Mes -{i}'
                )
                Movimiento.objects.filter(pk=m.pk).update(
                    fecha_registro=now - timezone.timedelta(days=30*i)
                )
                m = Movimiento.objects.create(
                    usuario=usuario, tipo='EGRESO', categoria=cat_egreso,
                    monto=500.00, descripcion=f'Renta Mes -{i}'
                )
                Movimiento.objects.filter(pk=m.pk).update(
                    fecha_registro=now - timezone.timedelta(days=30*i)
                )

            Movimiento.objects.create(
                usuario=usuario, tipo='INGRESO', categoria=cat_ingreso,
                monto=3000.00, descripcion='Bono sorpresa'
            )

            for i in range(5):
                Movimiento.objects.create(
                    usuario=usuario, tipo='EGRESO', categoria=cat_egreso,
                    monto=5.00, descripcion=f'Café {i}'
                )

            Movimiento.objects.create(
                usuario=usuario, tipo='EGRESO', categoria=cat_egreso,
                monto=2800.00, descripcion='Compra impulsiva de TV'
            )

        self.stdout.write(self.style.SUCCESS('\n¡Listo! Datos de prueba generados para TODOS los usuarios. Revisa la UI con tu cuenta.'))

        # Esperar a que terminen las tareas en background para no cortar el intérprete
        from notificaciones.dispatcher import NotificationDispatcher
        NotificationDispatcher._executor.shutdown(wait=True)
