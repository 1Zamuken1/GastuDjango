"""Admin panel para agente_financiero."""

from django.contrib import admin

from .models import AlertaDiaria, MensajeChat


@admin.register(MensajeChat)
class MensajeChatAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'rol', 'creado_en']
    list_filter = ['rol', 'creado_en']
    search_fields = ['usuario__username', 'contenido']
    date_hierarchy = 'creado_en'


@admin.register(AlertaDiaria)
class AlertaDiariaAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'generado_en', 'visto_en']
    list_filter = ['generado_en']
    search_fields = ['usuario__username']
