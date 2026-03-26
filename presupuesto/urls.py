from django.urls import path
from presupuesto import views

urlpatterns = [
    path('', views.base_presupuesto, name= "base_presupuesto"),
]