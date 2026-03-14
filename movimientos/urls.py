from django.urls import path

from . import views

app_name = 'movimientos'

urlpatterns = [
    path('ingresos/', views.lista_ingresos, name='ingresos'),
    path('egresos/', views.lista_egresos, name='egresos'),
    path('guardar/', views.guardar_movimiento, name='guardar_movimiento'),
    path('guardar/<int:pk>/', views.guardar_movimiento, name='editar_movimiento'),
    path('eliminar/<int:pk>/', views.eliminar_movimiento, name='eliminar_movimiento'),
    path('registros-categoria/', views.registros_por_categoria, name='registros_por_categoria'),
    path('resumen/', views.resumen_movimientos, name='resumen_movimientos'),
    path('buscar/', views.buscar_registros, name='buscar_registros'),
]