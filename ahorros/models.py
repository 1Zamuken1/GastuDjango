from django.db import models

# Create your models here.

class AhorroMeta(models.Model):
    
    class Frecuencia(models.TextChoices):
        DIARIA= 'DIARIA', 'Diaria',
        SEMANAL= 'SEMANAL', 'Semanal',
        QUINCENAL= 'QUINCENAL', 'Quincenal',
        MENSUAL='MENSUAL', 'Mensual',
        TRIMESTRAL='TRIMESTRAL', 'Trimestral',
        SEMESTRAL='SEMESTRAL', 'Semestral',
        ANUAL='ANUAL', 'Anual'
        
    class Estado(models.TextChoices):
        SIN_INICIAR='SIN_INICIAR', 'Sin_iniciar',
        ACTIVO='ACTIVO', 'Activo',
        COMPLETADO='COMPLETADO', 'Completado',
        ABANDONADO='ABANDONADO', 'Abandonado',
        
    monto_meta=models.DecimalField(max_digits=12, decimal_places=2, null=False)
    total_acumulado=models.DecimalField(max_digits=12, decimal_places=2, null=False, default=0)
    frecuencia=models.CharField(max_length=15, choices=Frecuencia.choices, null=False)
    fecha_creacion = models.DateField(auto_now_add=True, null=False)
    fecha_meta=models.DateField(null=False)
    estado= models.CharField(max_length=25, choices=Estado.choices, null=False, default=Estado.SIN_INICIAR.value)
    cantidad_cuotas=models.IntegerField(null=False)
    descripcion=models.CharField(max_length=150, blank=True)
    categoria = models.ForeignKey("categorias.categoria", on_delete= models.CASCADE, null=False)
    usuario = models.ForeignKey("usuarios.usuario", on_delete=models.CASCADE, null=False)
    
    class Meta:
        verbose_name = 'Meta de Ahorro'
        verbose_name_plural = 'Metas de Ahorro'
        ordering = ['-fecha_creacion'] # El '-' hace que la más nueva salga primero
        
    def __str__(self):
        return f"{self.categoria} - {self.descripcion} - {self.monto_meta}"
    
    
class AporteAhorro(models.Model):
    
    class EstadoAp(models.TextChoices):
        APORTADO= 'APORTADO', 'Aportado',
        PERDIDO= 'PERDIDO', 'Perdido',
        PENDIENTE='PENDIENTE', 'Pendiente'
        
    aporte_asignado=models.DecimalField(max_digits=12, decimal_places=2 )
    aporte = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    fecha_limite=models.DateField(null=False)
    estado_ap=models.CharField(max_length=15, choices=EstadoAp.choices, null=False)
    fecha_registro = models.DateField(auto_now_add=True, null=False)
    ahorro=models.ForeignKey(AhorroMeta, on_delete=models.CASCADE, null=False)
    es_extraordinario = models.BooleanField(default=False)
    
    
    
    class Meta:
        verbose_name = 'Aporte de Ahorro'
        verbose_name_plural = 'Aportes de Ahorro' 
        
    def __str__(self):
        return f"{self.aporte_asignado} - {self.aporte} "
    
    