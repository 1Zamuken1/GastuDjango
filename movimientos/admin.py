from django.contrib import admin
from .models import Categoria, Movimiento


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    """Gestión de categorías desde el panel de administración."""
    list_display = ['nombre', 'tipo', 'activo', 'fecha_creacion']
    list_filter = ['tipo', 'activo']
    search_fields = ['nombre']


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    """Gestión de movimientos desde el panel de administración."""
    list_display = ['usuario', 'tipo', 'monto', 'categoria', 'activo', 'fecha_registro']
    list_filter = ['tipo', 'activo', 'categoria']
    search_fields = ['usuario__username', 'descripcion']