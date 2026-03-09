from django.db import models

class Presupuesto(models.Model):
    limite = models.DecimalField(max_digits=10,max_length=2)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    isActivo = models.BooleanField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    categoria = models.ForeignKey(Categoria, on_delete= models.CASCADE)
