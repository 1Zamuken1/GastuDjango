from django.urls import path
from . import views

app_name = 'panel_admin'

urlpatterns = [
    # Dashboard
    path('', views.admin_home, name='home'),

    # Perfil
    path('perfil/', views.admin_perfil, name='perfil'),

    # Usuarios — listado
    path('usuarios/', views.admin_usuarios, name='usuarios'),

    # Usuarios — CRUD JSON (modales)
    path('usuarios/crear/', views.admin_crear_usuario_ajax, name='crear_usuario'),
    path('usuarios/<int:usuario_id>/detalle/', views.admin_usuario_detalle, name='usuario_detalle'),
    path('usuarios/<int:usuario_id>/editar/', views.admin_editar_usuario_ajax, name='editar_usuario'),
    path('usuarios/<int:usuario_id>/toggle/', views.admin_toggle_usuario, name='toggle_usuario'),
    path('usuarios/<int:usuario_id>/rol/', views.admin_cambiar_rol, name='cambiar_rol'),
    path('usuarios/<int:usuario_id>/eliminar/', views.admin_eliminar_usuario, name='eliminar_usuario'),

    # Categorías — listado
    path('categorias/', views.admin_categorias, name='categorias'),

    # Categorías — CRUD JSON (modales)
    path('categorias/crear/', views.admin_crear_categoria_ajax, name='crear_categoria'),
    path('categorias/<int:categoria_id>/detalle/', views.admin_categoria_detalle, name='categoria_detalle'),
    path('categorias/<int:categoria_id>/editar/', views.admin_editar_categoria_ajax, name='editar_categoria'),
    path('categorias/<int:categoria_id>/toggle/', views.admin_toggle_categoria, name='toggle_categoria'),

    # Categorías — Importacion masiva CSV
    path('categorias/importar/', views.importar_categorias_csv, name='importar_categorias_csv'),
]