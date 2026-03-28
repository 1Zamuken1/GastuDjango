from django.urls import path
from . import views

app_name = 'historial'

urlpatterns = [
    path('api/listar/', views.api_listar_historial, name='api_listar'),
]
