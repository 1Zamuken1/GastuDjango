from django.db import models

# Create your models here.

class AhorroMeta(models.Model):
    
    class Frecuencia(models.TextChoices):
        DIARIA= 'DIARIA', 'Diaria',
        SEMANAL= 'SEMANAL', 'Semanal',
        QUINCENAL= 'QUINCENAL', 'Quincenal',
        MENSUAL='MENSUAL', 'Mensual',
        TRIMESTRAL='TRIMESTRAL', 'Trimestral'
        SEMESTRAL='SEMESTRAL', 'Semestral',
        ANUAL='ANUAL', 'Anual'
        
    montoMeta=models.DecimalField(max_digits=12, decimal_places=2)
    totalAcumulado=models.DecimalField(max_digits=12, decimal_places=2)
    frecuencia=models.CharField(max_length=15, choices=Frecuencia.choices)
    fechaCreacion = models.DateField(auto_now_add=True)
    fechaMeta=models.DateField(blank=True)
    estado= models.BooleanField()
    cantidadCuotas=models.IntegerField()
    descripcion=models.CharField(max_length=255)
    categoria = models.ForeignKey("categorias.Categoria", on_delete= models.CASCADE)
    usuario = models.ForeignKey("usuarios.Usuario", on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = 'Meta de Ahorro'
        verbose_name_plural = 'Metas de Ahorro'
        ordering = ['-fechaCreacion'] # El '-' hace que la más nueva salga primero
        
    def __str__(self):
        return f"{self.descripcion} - {self.montoMeta}"
    
    
class AporteAhorro(models.Model):
    aporteAsignado=models.DecimalField(max_digits=12, decimal_places=2 )
    aporte=models.DecimalField(max_digits=12, decimal_places=2)
    fechaLimite=models.DateField()
    estadoAp=models.BooleanField()
    fechaRegistro = models.DateField(auto_now_add=True)
    ahorro=models.ForeignKey(AhorroMeta, on_delete=models.CASCADE)
    
    
    class Meta:
        verbose_name = 'Aporte de Ahorro'
        verbose_name_plural = 'Aportes de Ahorro' 