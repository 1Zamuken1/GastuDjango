from rest_framework.routers import DefaultRouter
from categorias.api_views import CategoriaViewSet, categorias_egreso
from django.urls import path

router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet)

urlpatterns = [
    path('categorias-egreso/', categorias_egreso),
]+router.urls