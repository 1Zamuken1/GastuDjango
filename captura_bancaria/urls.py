from django.urls import path

from . import views
from .interruptor import requiere_captura

app_name = 'captura_bancaria'

urlpatterns = [
    path('', requiere_captura(views.captura_view), name='captura'),
    path('api/ingesta/', requiere_captura(views.ingesta), name='ingesta'),
    path('api/buzon/', requiere_captura(views.api_buzon), name='api_buzon'),
    path('api/buzon/regenerar/', requiere_captura(views.api_buzon_regenerar), name='api_buzon_regenerar'),
    path('api/resumen/', requiere_captura(views.api_resumen), name='api_resumen'),
    path('api/prueba/', requiere_captura(views.api_prueba), name='api_prueba'),
    path('api/detectados/', requiere_captura(views.api_detectados), name='api_detectados'),
    path('api/reglas/', requiere_captura(views.api_reglas), name='api_reglas'),
    path('api/reglas/crear/', requiere_captura(views.api_regla_crear), name='api_regla_crear'),
    path('api/reglas/<int:pk>/actualizar/', requiere_captura(views.api_regla_actualizar), name='api_regla_actualizar'),
    path('api/reglas/<int:pk>/eliminar/', requiere_captura(views.api_regla_eliminar), name='api_regla_eliminar'),
    path('api/detectados/lote/confirmar/', requiere_captura(views.api_confirmar_lote), name='api_confirmar_lote'),
    path('api/detectados/<int:pk>/confirmar/', requiere_captura(views.api_confirmar), name='api_confirmar'),
    path('api/detectados/<int:pk>/descartar/', requiere_captura(views.api_descartar), name='api_descartar'),
]
