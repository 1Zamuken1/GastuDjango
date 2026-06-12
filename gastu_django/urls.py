from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap
from landing.sitemaps import StaticViewSitemap
from django.conf import settings

sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
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
    path('notificaciones/', include('notificaciones.urls', namespace='notificaciones')),
    path('historial/', include('historial.urls', namespace='historial')),

    # OAuth
    path('auth/', include('allauth.urls')),
]

# Tailwind hot reload (solo DEBUG)
if settings.DEBUG:
    urlpatterns += [
        path('__reload__/', include('django_browser_reload.urls')),
    ]