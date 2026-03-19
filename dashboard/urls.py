from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('tendencia/', views.tendencia_mes, name='tendencia_mes'),
]