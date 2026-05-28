from django.contrib import admin
from .models import PreferenciasAlertas


@admin.register(PreferenciasAlertas)
class PreferenciasAlertasAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'umbral_advertencia_porcentaje', 'egreso_grande_porcentaje')
    search_fields = ('usuario__email', 'usuario__username')
    readonly_fields = ('usuario',)
