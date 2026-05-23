from django.urls import path
from . import views

app_name = 'notificaciones'

urlpatterns = [
    path('json/', views.notificaciones_json, name='notificaciones_json'),
    path('marcar-leidas/', views.notificaciones_marcar_leidas,
         name='notificaciones_marcar_leidas'),
]
