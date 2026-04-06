from django.db import models


class Programacion(models.Model):

    class Frecuencia(models.TextChoices):
        DIARIO     = 'DIARIO',     'Diario'
        SEMANAL    = 'SEMANAL',    'Semanal'
        QUINCENAL  = 'QUINCENAL',  'Quincenal'
        MENSUAL    = 'MENSUAL',    'Mensual'
        BIMESTRAL  = 'BIMESTRAL',  'Bimestral'
        TRIMESTRAL = 'TRIMESTRAL', 'Trimestral'
        SEMESTRAL  = 'SEMESTRAL',  'Semestral'
        ANUAL      = 'ANUAL',      'Anual'

    monto_programado = models.DecimalField(max_digits=12, decimal_places=2)
    tipo             = models.CharField(max_length=10)
    descripcion      = models.CharField(max_length=100, blank=True, null=True)
    fecha_inicio     = models.DateField()
    fecha_fin        = models.DateField(blank=True, null=True)
    frecuencia       = models.CharField(max_length=30, choices=Frecuencia.choices)
    proxima_ejecucion = models.DateField(blank=True, null=True)
    activo           = models.BooleanField(default=True)
    fecha_creacion   = models.DateTimeField(auto_now_add=True)
    categoria        = models.ForeignKey("categorias.Categoria", on_delete=models.CASCADE)
    usuario          = models.ForeignKey("usuarios.Usuario", on_delete=models.CASCADE)

    class Meta:
        verbose_name        = 'Programación'
        verbose_name_plural = 'Programaciones'
        ordering            = ['-fecha_creacion']

    def __str__(self):
        return f'{self.tipo} - {self.categoria} | {self.frecuencia} | ${self.monto_programado}'
class EjecucionProgramacion(models.Model):
    programacion      = models.ForeignKey(Programacion, on_delete=models.SET_NULL, null=True, blank=True, related_name='ejecuciones')
    usuario           = models.ForeignKey("usuarios.Usuario", on_delete=models.CASCADE, null=True)
    fecha_ejecutada   = models.DateField()
    proxima_ejecucion = models.DateField(null=True, blank=True)
    monto             = models.DecimalField(max_digits=12, decimal_places=2)
    categoria_nombre  = models.CharField(max_length=100)
    tipo              = models.CharField(max_length=10)
    descripcion_snapshot = models.CharField(max_length=100, blank=True, null=True)
    frecuencia_snapshot  = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        ordering = ['-fecha_ejecutada']

    def __str__(self):
        return f'{self.programacion} — {self.fecha_ejecutada}'