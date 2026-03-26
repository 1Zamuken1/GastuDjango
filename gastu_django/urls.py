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
    path('ahorros/', include('ahorros.urls')),
    #categoria api
    path('api/',include('categorias.api_urls')),
    #presupuestos - no me lo toquen sapas
    path('api/', include('presupuesto.api_urls')),
    path('presupuesto/', include('presupuesto.urls')),
]