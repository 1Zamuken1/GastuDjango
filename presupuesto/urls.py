from django.urls import path
from presupuesto import views

urlpatterns = [
path('', views.home),
path('listar/', views.listar_presupuestos, name = "listar_presupuestos"),
path("crear/", views.crear_presupuesto, name="crear_presupuesto"),
path("editar/<int:id>/", views.editar_presupuesto, name="editar_presupuesto"),
path("confirmarEditar/<int:id>/", views.confirmar_editar_presupuesto, name="confirmar_editar_presupuesto"),
path("eliminar/<int:id>/", views.eliminar_presupuesto, name="eliminar_presupuesto"),

]