from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado que extiende AbstractUser de Django.
    AbstractUser ya provee: username, email, password, first_name,
    last_name, is_active, is_staff, date_joined.
    """

    class Rol(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        USER = 'USER', 'Usuario'

    telefono = models.CharField(max_length=20, blank=True, null=True)
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.USER)

    def __str__(self):
        return self.username


class Preferencias(models.Model):
    """
    Configuración de alertas y notificaciones de un usuario.
    Origen: creada automáticamente al registrar un Usuario.
    Destino: módulo de Notificaciones para evaluar umbrales.
    """

    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='preferencias'
    )

    umbral_advertencia_porcentaje = models.IntegerField(default=80)
    egreso_grande_porcentaje = models.IntegerField(default=30)

    alerta_egreso_grande = models.BooleanField(default=True)
    alerta_deficit = models.BooleanField(default=True)
    alerta_patron_inusual = models.BooleanField(default=True)
    alerta_presupuesto = models.BooleanField(default=True)
    alerta_aporte_proximo = models.BooleanField(default=True)
    alerta_aporte_dias_anticipacion = models.IntegerField(default=3)

    def __str__(self):
        return f'Preferencias de {self.usuario.username}'