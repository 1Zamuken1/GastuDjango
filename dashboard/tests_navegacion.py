"""
tests/test_navegacion.py
========================
Tests del sistema de navegación: navbar y sidebar.
Verifica que todas las rutas principales existen, responden 200
para usuario autenticado, 302 para no autenticado, y que los
templates globales se cargan correctamente.

Ejecutar:  python manage.py test tests.test_navegacion
"""
from django.test import TestCase, Client
from django.urls import reverse
from categorias.models import Categoria
from usuarios.models import Usuario


class NavbarSidebarTestCase(TestCase):
    """Pruebas de navegación y accesibilidad de rutas principales."""

    def setUp(self):
        self.client = Client()
        # Usuario estándar
        self.user = Usuario.objects.create_user(
            email='nav@test.com',
            password='pass1234!',
            username='navtest'
        )
        # Admin para rutas de panel
        self.admin = Usuario.objects.create_user(
            email='navadmin@test.com',
            password='admin1234!',
            username='navadmin',
            rol='ADMIN',
            is_staff=True
        )
        self.client.login(email='nav@test.com', password='pass1234!')

    # ── Rutas públicas ────────────────────────────────────────────

    def test_ruta_login_abierta(self):
        """La ruta /login/ es accesible sin autenticación."""
        self.client.logout()
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_ruta_register_abierta(self):
        """La ruta /register/ es accesible sin autenticación."""
        self.client.logout()
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    # ── Rutas protegidas: usuario autenticado ─────────────────────

    def test_ruta_dashboard_autenticado(self):
        """GET /dashboard/ retorna 200 para usuario autenticado."""
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 200)

    def test_ruta_ingresos_autenticado(self):
        """GET /ingresos/ retorna 200 para usuario autenticado."""
        response = self.client.get(reverse('movimientos:ingresos'))
        self.assertEqual(response.status_code, 200)

    def test_ruta_egresos_autenticado(self):
        """GET /egresos/ retorna 200 para usuario autenticado."""
        response = self.client.get(reverse('movimientos:egresos'))
        self.assertEqual(response.status_code, 200)

    def test_ruta_perfil_autenticado(self):
        """GET /perfil/ retorna 200 para usuario autenticado."""
        response = self.client.get(reverse('perfil'))
        self.assertEqual(response.status_code, 200)

    # ── Rutas protegidas: sin autenticación ──────────────────────

    def test_ruta_dashboard_sin_sesion(self):
        """GET /dashboard/ redirige al login sin sesión."""
        self.client.logout()
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_ruta_ingresos_sin_sesion(self):
        """GET /ingresos/ redirige al login sin sesión."""
        self.client.logout()
        response = self.client.get(reverse('movimientos:ingresos'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_ruta_egresos_sin_sesion(self):
        """GET /egresos/ redirige al login sin sesión."""
        self.client.logout()
        response = self.client.get(reverse('movimientos:egresos'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_ruta_perfil_sin_sesion(self):
        """GET /perfil/ redirige al login sin sesión."""
        self.client.logout()
        response = self.client.get(reverse('perfil'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    # ── Templates base ────────────────────────────────────────────

    def test_dashboard_usa_template_base(self):
        """El dashboard extiende base_app.html."""
        response = self.client.get(reverse('dashboard:home'))
        self.assertTemplateUsed(response, 'base_app.html')

    def test_ingresos_usa_template_base(self):
        """La vista de ingresos extiende base_app.html."""
        response = self.client.get(reverse('movimientos:ingresos'))
        self.assertTemplateUsed(response, 'base_app.html')

    def test_egresos_usa_template_base(self):
        """La vista de egresos extiende base_app.html."""
        response = self.client.get(reverse('movimientos:egresos'))
        self.assertTemplateUsed(response, 'base_app.html')

    def test_perfil_usa_template_base(self):
        """La vista de perfil extiende base_app.html."""
        response = self.client.get(reverse('perfil'))
        self.assertTemplateUsed(response, 'base_app.html')

    # ── Panel Admin: control de acceso ───────────────────────────

    def test_panel_admin_usuario_normal_redirige(self):
        """Un usuario USER no puede acceder al panel de admin."""
        response = self.client.get(reverse('panel_admin:home'))
        self.assertEqual(response.status_code, 302)

    def test_panel_admin_admin_retorna_200(self):
        """Un usuario ADMIN puede acceder al panel de admin."""
        self.client.logout()
        self.client.login(email='navadmin@test.com', password='admin1234!')
        response = self.client.get(reverse('panel_admin:home'))
        self.assertEqual(response.status_code, 200)

    def test_panel_admin_sin_sesion_redirige_login(self):
        """Sin sesión, el panel de admin redirige al login."""
        self.client.logout()
        response = self.client.get(reverse('panel_admin:home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    # ── Sidebar: estado activo por ruta ──────────────────────────

    def test_dashboard_contiene_nav_link(self):
        """El dashboard renderiza un enlace de navegación activo."""
        response = self.client.get(reverse('dashboard:home'))
        # Verificar que el elemento de nav del sidebar existe en el HTML
        self.assertContains(response, 'nav-item')

    def test_ingresos_contiene_nav_link(self):
        """La vista de ingresos renderiza elementos de navegación."""
        response = self.client.get(reverse('movimientos:ingresos'))
        self.assertContains(response, 'nav-item')

    # ── Campana de notificaciones ─────────────────────────────────

    def test_topbar_contiene_campana(self):
        """La topbar incluye el elemento de la campana de notificaciones."""
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'notif-btn')

    def test_topbar_contiene_user_menu(self):
        """La topbar incluye el menú desplegable del usuario."""
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'user-avatar')
