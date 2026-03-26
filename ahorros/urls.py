from django.urls import path
from . import views
app_name = 'ahorros'

urlpatterns = [
    path('', views.listar, name='listar_ahorros'),
    path('crear/', views.crear_ahorro, name='crear_ahorro'),
    path('<int:id>/editar/', views.editar_ahorro, name='editar_ahorro'),
    path('<int:id>/eliminar/', views.eliminar_ahorro, name='eliminar_ahorro'),
    path('<int:meta_id>/aporte/', views.registrar_aporte, name='registrar_aporte'),
]

