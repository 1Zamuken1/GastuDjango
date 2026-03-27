from django.db import models
from django.conf import settings


class Notificacion(models.Model):
    """
    Registra alertas automáticas generadas por el sistema para un usuario.
    Origen: signals de Movimiento al crear/editar.
    Destino: vista de notificaciones del usuario.
    """

    class Tipo(models.TextChoices):
        # — Originales —
        UMBRAL_MENSUAL      = 'UMBRAL_MENSUAL',      'Umbral mensual alcanzado'
        EGRESO_GRANDE       = 'EGRESO_GRANDE',       'Egreso grande registrado'
        DEFICIT             = 'DEFICIT',             'Balance en déficit'

        # — Tendencias —
        GASTO_INCREMENTAL   = 'GASTO_INCREMENTAL',   'Gasto incremental detectado'
        REDUCCION_INGRESOS  = 'REDUCCION_INGRESOS',  'Reducción de ingresos detectada'
        PATRON_INUSUAL      = 'PATRON_INUSUAL',      'Patrón inusual de gastos'

        # — Conceptos —
        CONCENTRACION_GASTO = 'CONCENTRACION_GASTO', 'Concentración de gastos en concepto'
        CONCEPTO_SIN_USO    = 'CONCEPTO_SIN_USO',    'Concepto recurrente sin actividad'

        # — Tiempo —
        VELOCIDAD_GASTO     = 'VELOCIDAD_GASTO',     'Velocidad de gasto alta'
        INACTIVIDAD_INGRESOS= 'INACTIVIDAD_INGRESOS','Inactividad de ingresos'
        EGRESOS_AGRUPADOS   = 'EGRESOS_AGRUPADOS',   'Múltiples gastos en corto tiempo'

        # — Micro-gastos —
        MICRO_GASTOS        = 'MICRO_GASTOS',        'Múltiples micro-gastos detectados'
        GASTOS_HORMIGA      = 'GASTOS_HORMIGA',      'Gastos hormiga diarios'

        # — Predictivas —
        PROYECCION_SOBREGASTO = 'PROYECCION_SOBREGASTO', 'Proyección de sobregasto'
        COMPARACION_PERIODO   = 'COMPARACION_PERIODO',   'Comparación con mes anterior'
        DIA_MES_CRITICO       = 'DIA_MES_CRITICO',       'Día del mes crítico'

        # — Inconsistencias —
        EGRESO_SIN_CONCEPTO   = 'EGRESO_SIN_CONCEPTO',   'Egresos sin categorizar'
        INGRESO_INUSUAL       = 'INGRESO_INUSUAL',       'Ingreso inusualmente alto'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones',
    )
    tipo        = models.CharField(max_length=30, choices=Tipo.choices)
    titulo      = models.CharField(max_length=100)
    descripcion = models.TextField()
    leida       = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering            = ['-fecha_creacion']

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.usuario.username}'
    
    
    
    
    
    

# from django.db import models
# from django.conf import settings


# class Notificacion(models.Model):
#     """
#     Registra alertas automáticas generadas por el sistema para un usuario.
#     Origen: signals de Movimiento al crear/editar.
#     Destino: vista de notificaciones del usuario.
#     """

#     class Tipo(models.TextChoices):
#         UMBRAL_MENSUAL = 'UMBRAL_MENSUAL', 'Umbral mensual alcanzado'
#         EGRESO_GRANDE = 'EGRESO_GRANDE', 'Egreso grande registrado'
#         DEFICIT = 'DEFICIT', 'Balance en déficit'

#     usuario = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name='notificaciones'
#     )
#     tipo = models.CharField(max_length=20, choices=Tipo.choices)
#     titulo = models.CharField(max_length=100)
#     descripcion = models.CharField(max_length=255)
#     leida = models.BooleanField(default=False)
#     fecha_creacion = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         verbose_name = 'Notificación'
#         verbose_name_plural = 'Notificaciones'
#         ordering = ['-fecha_creacion']

#     def __str__(self):
#         return f'{self.tipo} - {self.usuario.username}'
