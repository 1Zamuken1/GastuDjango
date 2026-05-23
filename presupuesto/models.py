from django.db import models


class Presupuesto(models.Model):
    """Límite de gasto definido por el usuario para una categoría en un rango de fechas."""
    limite = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_inicio = models.DateField(db_index=True)
    fecha_fin = models.DateField(db_index=True)
    isActivo = models.BooleanField(db_index=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    categoria = models.ForeignKey("categorias.Categoria", on_delete=models.CASCADE, db_index=True)
    usuario = models.ForeignKey("usuarios.Usuario", on_delete=models.CASCADE, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['usuario', 'isActivo']),
            models.Index(fields=['usuario', 'categoria', 'isActivo']),
            models.Index(fields=['fecha_inicio', 'fecha_fin']),
        ]