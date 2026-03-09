from django.db import models
from django.conf import settings


class Notificacion(models.Model):
    """
    Registra alertas automáticas generadas por el sistema para un usuario.
    Origen: signals de Movimiento al crear/editar.
    Destino: vista de notificaciones del usuario.
    """

    class Tipo(models.TextChoices):
        UMBRAL_MENSUAL = 'UMBRAL_MENSUAL', 'Umbral mensual alcanzado'
        EGRESO_GRANDE = 'EGRESO_GRANDE', 'Egreso grande registrado'
        DEFICIT = 'DEFICIT', 'Balance en déficit'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones'
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    titulo = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255)
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.tipo} - {self.usuario.username}'