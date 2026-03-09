from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_preferencias_al_registrar(sender, instance, created, **kwargs):
    """
    Crea las preferencias por defecto cuando se registra un nuevo usuario.

    Args:
        instance: instancia del Usuario creado.
        created (bool): True si es un registro nuevo.
    """
    if created:
        from .models import Preferencias
        Preferencias.objects.create(usuario=instance)