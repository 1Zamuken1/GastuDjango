from django.urls import path
from rest_framework.routers import DefaultRouter
from .api_views import ProgramacionViewSet
from .api_pendientes import programaciones_pendientes, ejecutar_programacion, historial_ejecuciones

router = DefaultRouter()
router.register(r'programaciones', ProgramacionViewSet, basename='programacion')

urlpatterns = [
    path('programaciones/pendientes/', programaciones_pendientes),
    path('programaciones/historial/', historial_ejecuciones),       
    path('programaciones/<int:pk>/ejecutar/', ejecutar_programacion),
] + router.urls