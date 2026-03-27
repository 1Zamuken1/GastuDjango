from rest_framework.routers import DefaultRouter
from .api_views import PresupuestoViewSet

router = DefaultRouter()
router.register(r'presupuestos', PresupuestoViewSet)

urlpatterns = router.urls