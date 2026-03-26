# urls.py

from rest_framework.routers import DefaultRouter
from categorias.api_views import CategoriaViewSet

router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet)

urlpatterns = router.urls