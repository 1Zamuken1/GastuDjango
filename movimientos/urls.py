from django.urls import path

from . import views
from . import views_api
from . import views_exportar

app_name = 'movimientos'

urlpatterns = [
    # ── Vistas de página (devuelven HTML) ────────────────────────────────────
    path('ingresos/', views.lista_ingresos, name='ingresos'),
    path('egresos/',  views.lista_egresos,  name='egresos'),

    # ── Endpoints CRUD usados por el frontend (FormData + sesión) ────────────
    path('guardar/',           views.guardar_movimiento,    name='guardar_movimiento'),
    path('guardar/<int:pk>/',  views.guardar_movimiento,    name='editar_movimiento'),
    path('eliminar/<int:pk>/', views.eliminar_movimiento,   name='eliminar_movimiento'),

    # ── Endpoints de consulta usados por el frontend ──────────────────────────
    path('registros-categoria/', views.registros_por_categoria, name='registros_por_categoria'),
    path('resumen/',             views.resumen_movimientos,     name='resumen_movimientos'),
    path('buscar/',              views.buscar_registros,        name='buscar_registros'),

    # ── Exportación ───────────────────────────────────────────────────────────
    path('exportar/csv/',   views_exportar.exportar_csv,   name='exportar_csv'),
    path('exportar/excel/', views_exportar.exportar_excel, name='exportar_excel'),
    path('exportar/pdf/',   views_exportar.exportar_pdf,   name='exportar_pdf'),

    # ── API REST para el agente_financiero (JSON puro) ────────────────────────
    # Lectura
    path('api/listar/',     views_api.api_listar_movimientos, name='api_listar'),
    path('api/categorias/', views_api.api_listar_categorias,  name='api_categorias'),
    # Escritura
    path('api/crear/',              views_api.api_crear_movimiento,   name='api_crear'),
    path('api/editar/<int:pk>/',    views_api.api_editar_movimiento,  name='api_editar'),
    path('api/eliminar/<int:pk>/',  views_api.api_eliminar_movimiento, name='api_eliminar'),
]