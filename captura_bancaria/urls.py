from django.urls import path

from . import views

app_name = 'captura_bancaria'

urlpatterns = [
    path('', views.captura_view, name='captura'),
    path('api/ingesta/', views.ingesta, name='ingesta'),
    path('api/buzon/', views.api_buzon, name='api_buzon'),
    path('api/buzon/regenerar/', views.api_buzon_regenerar, name='api_buzon_regenerar'),
    path('api/resumen/', views.api_resumen, name='api_resumen'),
    path('api/detectados/', views.api_detectados, name='api_detectados'),
    path('api/reglas/', views.api_reglas, name='api_reglas'),
    path('api/reglas/crear/', views.api_regla_crear, name='api_regla_crear'),
    path('api/reglas/<int:pk>/actualizar/', views.api_regla_actualizar, name='api_regla_actualizar'),
    path('api/reglas/<int:pk>/eliminar/', views.api_regla_eliminar, name='api_regla_eliminar'),
    path('api/detectados/lote/confirmar/', views.api_confirmar_lote, name='api_confirmar_lote'),
    path('api/detectados/<int:pk>/confirmar/', views.api_confirmar, name='api_confirmar'),
    path('api/detectados/<int:pk>/descartar/', views.api_descartar, name='api_descartar'),
]
