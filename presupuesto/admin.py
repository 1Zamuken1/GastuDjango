from django.contrib import admin
from .models import Presupuesto

@admin.register(Presupuesto)
class PresupuestoAdmin(admin.ModelAdmin):
    list_display = ('id', 'categoria', 'usuario', 'limite', 'fecha_inicio', 'fecha_fin', 'is_activo')
    list_filter = ('is_activo', 'fecha_inicio', 'fecha_fin')
