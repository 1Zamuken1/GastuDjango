from django.db import models


class Categoria(models.Model):
    """
    Clasifica movimientos financieros por tipo.
    Gestionada por el Admin. Usada por Movimiento, AhorroMeta y Programacion.
    """

    class TipoCategoria(models.TextChoices):
        INGRESO = 'INGRESO', 'Ingreso'
        EGRESO = 'EGRESO', 'Egreso'
        AHORRO = 'AHORRO', 'Ahorro'

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TipoCategoria.choices)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.tipo})'