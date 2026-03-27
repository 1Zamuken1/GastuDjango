from django.urls import path
from . import views

urlpatterns = [
    path('json/', views.notificaciones_json, name='notificaciones_json'),
]