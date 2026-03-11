from django.contrib import admin
from .models import Movimiento
from categorias.models import Categoria   # ← FIX: importar desde categorias, no desde movimientos


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display  = ['nombre', 'tipo', 'activo', 'fecha_creacion']
    list_filter   = ['tipo', 'activo']
    search_fields = ['nombre']


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display  = ['usuario', 'tipo', 'monto', 'categoria', 'activo', 'fecha_registro']
    list_filter   = ['tipo', 'activo', 'categoria']
    search_fields = ['usuario__username', 'descripcion']