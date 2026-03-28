from django.db import models
from django.conf import settings
from movimientos.models import ModeloBase

class AccionHistorial(ModeloBase):
    class AccionChoices(models.TextChoices):
        CREACION = 'CREACION', 'Creación'
        EDICION = 'EDICION', 'Edición'
        ELIMINACION = 'ELIMINACION', 'Eliminación'

    class ModuloChoices(models.TextChoices):
        INGRESOS = 'INGRESOS', 'Ingresos'
        EGRESOS = 'EGRESOS', 'Egresos'
        CATEGORIAS = 'CATEGORIAS', 'Categorias'
        AHORROS = 'AHORROS', 'Ahorros'
        PRESUPUESTOS = 'PRESUPUESTOS', 'Presupuestos'
        PROYECCIONES = 'PROYECCIONES', 'Proyecciones'
        SISTEMA = 'SISTEMA', 'Sistema'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='acciones_historial'
    )
    accion = models.CharField(max_length=15, choices=AccionChoices.choices)
    modulo = models.CharField(max_length=20, choices=ModuloChoices.choices)
    descripcion = models.CharField(max_length=255)
    
    # Puede guardar el ID o UUID del objeto afectado (se usa CharField por flexibilidad)
    referencia_id = models.CharField(max_length=50, blank=True, null=True)
    monto_afectado = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # fecha_creacion provista por ModeloBase servirá como fecha de registro

    class Meta:
        verbose_name = 'Acción de Historial'
        verbose_name_plural = 'Acciones de Historial'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.usuario.username} - {self.get_accion_display()} en {self.get_modulo_display()}"
