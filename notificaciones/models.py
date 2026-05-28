from django.db import models
from django.conf import settings
from .preferencias.models import PreferenciasAlertas


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
        
        # — Ahorros —
        RECORDATORIO_CUOTA_AHORRO = 'RECORDATORIO_CUOTA_AHORRO', 'Recordatorio de cuota de ahorro'

        # — Inconsistencias —
        EGRESO_SIN_CONCEPTO   = 'EGRESO_SIN_CONCEPTO',   'Egresos sin categorizar'
        INGRESO_INUSUAL       = 'INGRESO_INUSUAL',       'Ingreso inusualmente alto'

    class Modulo(models.TextChoices):
        """Clasificacion de notificaciones por modulo que las genera."""
        INGRESOS      = 'INGRESOS',      'Ingresos'
        EGRESOS       = 'EGRESOS',       'Egresos'
        AHORROS       = 'AHORROS',       'Ahorros'
        PRESUPUESTOS  = 'PRESUPUESTOS',  'Presupuestos'
        PLANIFICACION = 'PLANIFICACION', 'Planificacion'
        GENERAL       = 'GENERAL',       'General'

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
    modulo      = models.CharField(
        max_length=20,
        choices=Modulo.choices,
        default=Modulo.GENERAL,
    )
    referencia_id = models.PositiveIntegerField(null=True, blank=True)
    referencia_tipo = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Ej: 'movimiento', 'ahorro', 'programacion', 'sistema'"
    )

    @classmethod
    def modulo_por_tipo(cls, tipo):
        """
        Devuelve el modulo correspondiente a un tipo de notificacion.
        Usado por _crear_notificacion para clasificar automaticamente.
        """
        tipos_ingreso = {
            cls.Tipo.REDUCCION_INGRESOS,
            cls.Tipo.INACTIVIDAD_INGRESOS,
            cls.Tipo.CONCEPTO_SIN_USO,
            cls.Tipo.INGRESO_INUSUAL,
        }
        if tipo in tipos_ingreso:
            return cls.Modulo.INGRESOS

        tipos_egreso = {
            cls.Tipo.DEFICIT,
            cls.Tipo.EGRESO_GRANDE,
            cls.Tipo.UMBRAL_MENSUAL,
            cls.Tipo.GASTO_INCREMENTAL,
            cls.Tipo.CONCENTRACION_GASTO,
            cls.Tipo.VELOCIDAD_GASTO,
            cls.Tipo.PATRON_INUSUAL,
            cls.Tipo.PROYECCION_SOBREGASTO,
            cls.Tipo.COMPARACION_PERIODO,
            cls.Tipo.MICRO_GASTOS,
            cls.Tipo.GASTOS_HORMIGA,
            cls.Tipo.EGRESOS_AGRUPADOS,
            cls.Tipo.DIA_MES_CRITICO,
            cls.Tipo.EGRESO_SIN_CONCEPTO,
        }
        if tipo in tipos_egreso:
            return cls.Modulo.EGRESOS

        tipos_ahorro = {
            cls.Tipo.RECORDATORIO_CUOTA_AHORRO,
        }
        if tipo in tipos_ahorro:
            return cls.Modulo.AHORROS

        return cls.Modulo.GENERAL

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
