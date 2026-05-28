from django.contrib import admin
from .models import Notificacion

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo', 'modulo', 'leida', 'fecha_creacion')
    list_filter = ('leida', 'modulo', 'tipo')
    search_fields = ('usuario__username', 'titulo')
