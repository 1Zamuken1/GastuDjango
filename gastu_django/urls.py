from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('landing.urls', namespace='landing')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('', include('usuarios.urls')),
    path('', include('movimientos.urls', namespace='movimientos')),
    path('categorias/', include('categorias.urls', namespace='categorias')),
    path('admin-panel/', include('panel_admin.urls', namespace='panel_admin')),
    path('ahorros/', include('ahorros.urls', namespace='ahorros')),

    # APIs
    path('api/', include('categorias.api_urls')),
    path('api/', include('presupuesto.api_urls')),
    path('api/', include('programaciones.api_urls')),
    path('api/', include('agente_financiero.api_urls')),

    # Módulos
    path('presupuesto/', include('presupuesto.urls')),
    path('programaciones/', include('programaciones.urls')),
    path('agente_financiero/', include('agente_financiero.urls')),

    # Otros
    path('notificaciones/', include('notificaciones.urls')),
    path('historial/', include('historial.urls', namespace='historial')),

    # OAuth
    path('auth/', include('allauth.urls')),
]