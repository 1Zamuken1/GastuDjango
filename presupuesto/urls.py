from django.urls import path
from presupuesto import views
urlpatterns = [
    path('', views.home)
    ]