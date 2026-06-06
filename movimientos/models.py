from django.db import models
from django.conf import settings
from categorias.models import Categoria


class ModeloBase(models.Model):
    """
    Modelo abstracto base para todos los modelos del sistema.
    Provee campos comunes de auditoría y soft delete.
    No genera tabla propia.
    """
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


from django.utils import timezone

class Movimiento(ModeloBase):
    """
    Registra un ingreso o egreso financiero de un usuario.
    Origen: formulario del usuario autenticado.
    Destino: Dashboard (ResumenMensual), Notificaciones, Presupuesto.
    """

    class TipoMovimiento(models.TextChoices):
        INGRESO = 'INGRESO', 'Ingreso'
        EGRESO = 'EGRESO', 'Egreso'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='movimientos'
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='movimientos'
    )
    tipo = models.CharField(max_length=10, choices=TipoMovimiento.choices)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    fecha_registro = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Movimiento'
        verbose_name_plural = 'Movimientos'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f'{self.tipo} - ${self.monto} ({self.usuario.username})'

    @property
    def es_ingreso(self):
        """
        Verifica si el movimiento es un ingreso.

        Returns:
            bool: True si el tipo es INGRESO.
        """
        return self.tipo == self.TipoMovimiento.INGRESO

    @property
    def es_egreso(self):
        """
        Verifica si el movimiento es un egreso.

        Returns:
            bool: True si el tipo es EGRESO.
        """
        return self.tipo == self.TipoMovimiento.EGRESO