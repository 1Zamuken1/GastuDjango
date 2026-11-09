from django.contrib import admin

from .models import BuzonCaptura, CorreoEntrante, MovimientoDetectado, ReglaComercio


@admin.register(BuzonCaptura)
class BuzonCapturaAdmin(admin.ModelAdmin):
    list_display = ('alias', 'usuario', 'verificado', 'ultimo_correo_en', 'activo')
    search_fields = ('alias', 'usuario__email', 'usuario__username')


@admin.register(CorreoEntrante)
class CorreoEntranteAdmin(admin.ModelAdmin):
    list_display = ('recibido_en', 'buzon', 'remitente', 'asunto', 'estado', 'dkim_valido')
    list_filter = ('estado', 'dkim_valido')
    search_fields = ('remitente', 'asunto')


@admin.register(MovimientoDetectado)
class MovimientoDetectadoAdmin(admin.ModelAdmin):
    list_display = ('fecha_transaccion', 'usuario', 'banco', 'tipo', 'monto', 'comercio', 'estado')
    list_filter = ('estado', 'tipo', 'banco')
    search_fields = ('comercio', 'usuario__email')


@admin.register(ReglaComercio)
class ReglaComercioAdmin(admin.ModelAdmin):
    list_display = ('comercio_normalizado', 'usuario', 'tipo', 'categoria', 'auto_confirmar', 'veces_usada')
    search_fields = ('comercio_normalizado', 'usuario__email')
