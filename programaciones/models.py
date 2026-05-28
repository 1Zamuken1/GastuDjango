from django.db import models


class Programacion(models.Model):
    """Configuración recurrente de ingreso/egreso que se ejecuta automáticamente."""

    class Frecuencia(models.TextChoices):
        """Frecuencias de ejecución soportadas."""
        DIARIO     = 'DIARIO',     'Diario'
        SEMANAL    = 'SEMANAL',    'Semanal'
        QUINCENAL  = 'QUINCENAL',  'Quincenal'
        MENSUAL    = 'MENSUAL',    'Mensual'
        BIMESTRAL  = 'BIMESTRAL',  'Bimestral'
        TRIMESTRAL = 'TRIMESTRAL', 'Trimestral'
        SEMESTRAL  = 'SEMESTRAL',  'Semestral'
        ANUAL      = 'ANUAL',      'Anual'

    monto_programado = models.DecimalField(max_digits=12, decimal_places=2)
    tipo = models.CharField(max_length=10)
    descripcion = models.CharField(max_length=100, blank=True, null=True)
    fecha_inicio = models.DateField(db_index=True)
    fecha_fin = models.DateField(blank=True, null=True, db_index=True)
    frecuencia = models.CharField(max_length=30, choices=Frecuencia.choices, db_index=True)
    proxima_ejecucion = models.DateField(blank=True, null=True, db_index=True)
    activo = models.BooleanField(default=True, db_index=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    categoria = models.ForeignKey("categorias.Categoria", on_delete=models.CASCADE, db_index=True)
    usuario = models.ForeignKey("usuarios.Usuario", on_delete=models.CASCADE, db_index=True)

    class Meta:
        verbose_name = 'Programación'
        verbose_name_plural = 'Programaciones'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['usuario', 'activo']),
            models.Index(fields=['usuario', 'activo', 'frecuencia']),
            models.Index(fields=['fecha_inicio', 'fecha_fin']),
        ]

    def __str__(self):
        return f'{self.tipo} - {self.categoria} | {self.frecuencia} | ${self.monto_programado}'
