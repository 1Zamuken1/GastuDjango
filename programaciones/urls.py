from django.urls import path
from . import views

urlpatterns = [
    path('', views.base_programaciones, name= "base_programaciones"),
]   