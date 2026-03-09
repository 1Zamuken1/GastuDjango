from categorias.models import Categoria
from django.db import models

class Presupuesto(models.Model):
    limite = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    isActivo = models.BooleanField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    categoria = models.ForeignKey(Categoria, on_delete= models.CASCADE)
