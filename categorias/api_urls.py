from rest_framework.routers import DefaultRouter
from categorias.api_views import CategoriaViewSet, categorias_egreso, categorias_enriched, toggle_favorita
from django.urls import path

router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet)

urlpatterns = [
    path('categorias-egreso/', categorias_egreso),
    path('categorias/enriched/', categorias_enriched, name='categorias-enriched'),
    path('categorias/<int:pk>/toggle-favorita/', toggle_favorita, name='toggle-favorita'),
] + router.urls