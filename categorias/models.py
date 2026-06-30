from django.db import models


class Categoria(models.Model):
    """
    Clasifica movimientos financieros por tipo.
    Gestionada por el Admin. Usada por Movimiento, AhorroMeta y Programacion.
    """

    class TipoCategoria(models.TextChoices):
        INGRESO = 'INGRESO', 'Ingreso'
        EGRESO  = 'EGRESO',  'Egreso'
        AHORRO  = 'AHORRO',  'Ahorro'

    nombre         = models.CharField(max_length=100)
    tipo           = models.CharField(max_length=10, choices=TipoCategoria.choices)
    descripcion    = models.CharField(max_length=255, blank=True, null=True)
    activo         = models.BooleanField(default=True)
    es_sistema     = models.BooleanField(default=False, help_text='Ocultar al usuario en listados de creación')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering            = ['nombre']
        unique_together     = [['nombre', 'tipo']]

    def __str__(self):
        return f'{self.nombre} ({self.tipo})'


class CategoriaFavorita(models.Model):
    """Categoría marcada como favorita por un usuario específico."""
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE, related_name='categorias_favoritas')
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='favoritos')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['usuario', 'categoria']]
        verbose_name = 'Categoría Favorita'
        verbose_name_plural = 'Categorías Favoritas'

    def __str__(self):
        return f'{self.usuario.email} - {self.categoria.nombre}'