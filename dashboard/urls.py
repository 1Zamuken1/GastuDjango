from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('tendencia/', views.tendencia_mes, name='tendencia_mes'),
    path('meses-disponibles/', views.meses_disponibles, name='meses_disponibles'),
    path('exportar/excel/', views.exportar_excel, name='exportar_excel'),
    path('exportar/pdf/', views.exportar_pdf, name='exportar_pdf'),
]