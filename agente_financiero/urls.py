from django.urls import path
from . import views

urlpatterns = [
    path('', views.agente_financiero, name = 'agente_financiero')
]