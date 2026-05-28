from django.utils import timezone
from .models import Notificacion

class NotificacionRepository:
    @classmethod
    def guardar_si_no_existe(cls, usuario, alerta_data):
        """
        Anti-duplicado: solo guarda si no hay una notificación del mismo tipo 
        generada hoy (y no leída, opcionalmente, pero el plan original de GastuApp 
        es simplemente no spamear más de 1 vez al día por tipo).
        """
        hoy = timezone.now().date()
        tipo = alerta_data['tipo']
        referencia_id = alerta_data.get('referencia_id')

        qs = Notificacion.objects.filter(
            usuario=usuario,
            tipo=tipo,
            leida=False,
            fecha_creacion__date=hoy,
        )

        if referencia_id:
            qs = qs.filter(referencia_id=referencia_id)

        if qs.exists():
            return None

        modulo = Notificacion.modulo_por_tipo(tipo)
        return Notificacion.objects.create(
            usuario=usuario,
            tipo=tipo,
            titulo=alerta_data['titulo'],
            descripcion=alerta_data['descripcion'],
            modulo=modulo,
            referencia_id=alerta_data.get('referencia_id'),
            referencia_tipo=alerta_data.get('referencia_tipo')
        )

    @classmethod
    def marcar_como_leidas(cls, usuario, modulo='TODOS'):
        qs = Notificacion.objects.filter(usuario=usuario, leida=False)
        if modulo != 'TODOS':
            qs = qs.filter(modulo=modulo)
        return qs.update(leida=True)

    @classmethod
    def obtener_no_leidas(cls, usuario, modulo='TODOS', limite=50):
        qs = Notificacion.objects.filter(usuario=usuario, leida=False).order_by('-fecha_creacion')
        if modulo != 'TODOS':
            qs = qs.filter(modulo=modulo)
        return qs[:limite]
