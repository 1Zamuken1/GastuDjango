from django.urls import path
from . import views

app_name = 'movimientos'

urlpatterns = [
    path('ingresos/', views.lista_ingresos, name='lista_ingresos'),
    path('egresos/', views.lista_egresos, name='lista_egresos'),

    path('ingresos/categoria/<int:categoria_id>/', views.detalle_categoria, {'tipo': 'INGRESO'}, name='detalle_categoria_ingreso'),
    path('egresos/categoria/<int:categoria_id>/', views.detalle_categoria, {'tipo': 'EGRESO'}, name='detalle_categoria_egreso'),

    path('ingresos/crear/', views.crear_movimiento, {'tipo': 'INGRESO'}, name='crear_ingreso'),
    path('egresos/crear/', views.crear_movimiento, {'tipo': 'EGRESO'}, name='crear_egreso'),

    path('editar/<int:movimiento_id>/', views.editar_movimiento, name='editar_movimiento'),
    path('eliminar/<int:movimiento_id>/', views.eliminar_movimiento, name='eliminar_movimiento'),
]