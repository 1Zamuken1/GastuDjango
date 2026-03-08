from django.db import models
from django.conf import settings


class ResumenMensual(models.Model):
    """
    Almacena el resumen financiero de un usuario por mes y año.
    Origen: generado automáticamente al crear/editar/eliminar movimientos.
    Destino: validación de egresos, notificaciones, vista de dashboard.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='resumenes'
    )
    mes = models.IntegerField()
    anio = models.IntegerField()

    # Totales del mes
    total_ingresos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_egresos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_ahorros = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Calculados del mes
    ingreso_neto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    disponible = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Acumulados históricos — no se reinician
    ganancia_acumulada = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ahorro_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    fecha_actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Resumen mensual'
        verbose_name_plural = 'Resúmenes mensuales'
        ordering = ['-anio', '-mes']
        unique_together = ['usuario', 'mes', 'anio']

    def __str__(self):
        return f'Resumen {self.mes}/{self.anio} - {self.usuario.username}'

    @property
    def deficit(self):
        """
        Indica si el usuario tiene más egresos que ingresos en el mes.

        Returns:
            bool: True si total_egresos supera total_ingresos.
        """
        return self.total_egresos > self.total_ingresos