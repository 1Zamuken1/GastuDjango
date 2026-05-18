"""
tests/test_categorias.py
========================
Tests del módulo de gestión de categorías (panel_admin).
Cubre: listado, creación, edición, toggle activo/inactivo,
       validaciones y control de acceso por rol.

Ejecutar:  python manage.py test tests.test_categorias
"""
from django.test import TestCase, Client
from django.urls import reverse
from categorias.models import Categoria
from usuarios.models import Usuario


class CategoriasSetupMixin:
    """Mixin con la configuración común para tests de categorías."""

    def _crear_admin(self, email='admin@test.com', password='admin1234!'):
        return Usuario.objects.create_user(
            email=email,
            password=password,
            username='admintest',
            rol='ADMIN',
            is_staff=True
        )

    def _crear_user_normal(self, email='user@test.com', password='user1234!'):
        return Usuario.objects.create_user(
            email=email,
            password=password,
            username='usertest',
            rol='USER'
        )


class ListadoCategoriasTestCase(CategoriasSetupMixin, TestCase):
    """CU-07: Visualización del listado de categorías."""

    def setUp(self):
        self.client = Client()
        self.admin = self._crear_admin()
        self.client.login(email='admin@test.com', password='admin1234!')
        Categoria.objects.create(nombre='SalarioTest', tipo='INGRESO', activo=True)
        Categoria.objects.create(nombre='AlquilerTest', tipo='EGRESO', activo=True)
        Categoria.objects.create(nombre='InactivaTest', tipo='EGRESO', activo=False)

    def test_listado_retorna_200(self):
        """GET /admin/categorias/ retorna 200 para administrador."""
        response = self.client.get(reverse('panel_admin:categorias'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'panel_admin/categorias.html')

    def test_listado_muestra_categorias_activas(self):
        """El listado contiene las categorías activas registradas."""
        response = self.client.get(reverse('panel_admin:categorias'))
        self.assertContains(response, 'SalarioTest')
        self.assertContains(response, 'AlquilerTest')

    def test_listado_filtro_por_tipo(self):
        """Filtrar por tipo INGRESO devuelve solo ingresos."""
        response = self.client.get(reverse('panel_admin:categorias') + '?tipo=INGRESO')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SalarioTest')

    def test_listado_filtro_inactivas(self):
        """Filtrar por estado inactivo devuelve categorías inactivas."""
        response = self.client.get(reverse('panel_admin:categorias') + '?estado=inactivo')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'InactivaTest')

    def test_sin_sesion_redirige_login(self):
        """Sin autenticación, el listado redirige al login."""
        self.client.logout()
        response = self.client.get(reverse('panel_admin:categorias'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_usuario_normal_redirige_dashboard(self):
        """Un usuario sin rol ADMIN es redirigido al dashboard."""
        self.client.logout()
        user = self._crear_user_normal()
        self.client.login(email='user@test.com', password='user1234!')
        response = self.client.get(reverse('panel_admin:categorias'))
        self.assertEqual(response.status_code, 302)


class CreacionCategoriasTestCase(CategoriasSetupMixin, TestCase):
    """CU-09: Creación de categorías."""

    def setUp(self):
        self.client = Client()
        self.admin = self._crear_admin()
        self.client.login(email='admin@test.com', password='admin1234!')

    def test_crear_categoria_ingreso_exitoso(self):
        """Crear categoría tipo INGRESO retorna ok=True y la persiste en BD."""
        response = self.client.post(reverse('panel_admin:crear_categoria'), {
            'nombre': 'SalarioTest2',
            'tipo': 'INGRESO',
            'descripcion': 'Ingresos mensuales por empleo',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertTrue(Categoria.objects.filter(nombre='SalarioTest2', tipo='INGRESO').exists())

    def test_crear_categoria_egreso_exitoso(self):
        """Crear categoría tipo EGRESO retorna ok=True y la persiste en BD."""
        response = self.client.post(reverse('panel_admin:crear_categoria'), {
            'nombre': 'AlquilerTest2',
            'tipo': 'EGRESO',
            'descripcion': 'Pago mensual de arriendo',
        })
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertTrue(Categoria.objects.filter(nombre='AlquilerTest2', tipo='EGRESO').exists())

    def test_crear_categoria_sin_descripcion_exitoso(self):
        """Crear categoría sin descripción (campo opcional) funciona correctamente."""
        response = self.client.post(reverse('panel_admin:crear_categoria'), {
            'nombre': 'TransporteTest2',
            'tipo': 'EGRESO',
            'descripcion': '',
        })
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertTrue(Categoria.objects.filter(nombre='TransporteTest2', tipo='EGRESO').exists())

    def test_crear_categoria_nombre_vacio_falla(self):
        """Crear categoría sin nombre retorna ok=False."""
        response = self.client.post(reverse('panel_admin:crear_categoria'), {
            'nombre': '',
            'tipo': 'INGRESO',
            'descripcion': 'Sin nombre',
        })
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertIn('obligatorios', data.get('msg', '').lower())

    def test_crear_categoria_tipo_vacio_falla(self):
        """Crear categoría sin tipo retorna ok=False."""
        response = self.client.post(reverse('panel_admin:crear_categoria'), {
            'nombre': 'Bonificacion',
            'tipo': '',
            'descripcion': '',
        })
        data = response.json()
        self.assertFalse(data['ok'])

    def test_crear_categoria_duplicada_falla(self):
        """Crear categoría con nombre+tipo duplicado retorna ok=False."""
        Categoria.objects.create(nombre='SalarioTest3', tipo='INGRESO')
        response = self.client.post(reverse('panel_admin:crear_categoria'), {
            'nombre': 'SalarioTest3',
            'tipo': 'INGRESO',
            'descripcion': '',
        })
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertEqual(Categoria.objects.filter(nombre__iexact='SalarioTest3', tipo='INGRESO').count(), 1)

    def test_crear_sin_permiso_admin_falla(self):
        """Un usuario no-admin no puede crear categorías."""
        self.client.logout()
        user = self._crear_user_normal()
        self.client.login(email='user@test.com', password='user1234!')
        response = self.client.post(reverse('panel_admin:crear_categoria'), {
            'nombre': 'Intento', 'tipo': 'INGRESO',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Categoria.objects.filter(nombre='Intento').exists())


class EdicionCategoriasTestCase(CategoriasSetupMixin, TestCase):
    """CU-10: Edición de categorías."""

    def setUp(self):
        self.client = Client()
        self.admin = self._crear_admin()
        self.client.login(email='admin@test.com', password='admin1234!')
        self.categoria = Categoria.objects.create(
            nombre='ServiciosTest', tipo='EGRESO', activo=True
        )

    def test_editar_nombre_exitoso(self):
        """Editar el nombre de una categoría actualiza el registro en BD."""
        response = self.client.post(
            reverse('panel_admin:editar_categoria', args=[self.categoria.pk]),
            {'nombre': 'Servicios Publicos', 'tipo': 'EGRESO', 'descripcion': ''}
        )
        data = response.json()
        self.assertTrue(data['ok'])
        self.categoria.refresh_from_db()
        self.assertEqual(self.categoria.nombre, 'Servicios Publicos')

    def test_editar_tipo_exitoso(self):
        """Editar el tipo de una categoría actualiza el registro en BD."""
        response = self.client.post(
            reverse('panel_admin:editar_categoria', args=[self.categoria.pk]),
            {'nombre': 'ServiciosTest', 'tipo': 'INGRESO', 'descripcion': ''}
        )
        data = response.json()
        self.assertTrue(data['ok'])
        self.categoria.refresh_from_db()
        self.assertEqual(self.categoria.tipo, 'INGRESO')

    def test_editar_nombre_vacio_falla(self):
        """Editar categoría borrando el nombre retorna ok=False."""
        response = self.client.post(
            reverse('panel_admin:editar_categoria', args=[self.categoria.pk]),
            {'nombre': '', 'tipo': 'EGRESO', 'descripcion': ''}
        )
        data = response.json()
        self.assertFalse(data['ok'])

    def test_editar_nombre_duplicado_falla(self):
        """Editar categoría con nombre de otra ya existente retorna ok=False."""
        Categoria.objects.create(nombre='AlimentacionTest', tipo='EGRESO')
        response = self.client.post(
            reverse('panel_admin:editar_categoria', args=[self.categoria.pk]),
            {'nombre': 'AlimentacionTest', 'tipo': 'EGRESO', 'descripcion': ''}
        )
        data = response.json()
        self.assertFalse(data['ok'])

    def test_editar_sin_permiso_admin_falla(self):
        """Un usuario no-admin no puede editar categorías."""
        self.client.logout()
        self._crear_user_normal()
        self.client.login(email='user@test.com', password='user1234!')
        response = self.client.post(
            reverse('panel_admin:editar_categoria', args=[self.categoria.pk]),
            {'nombre': 'Hackeado', 'tipo': 'EGRESO', 'descripcion': ''}
        )
        self.assertEqual(response.status_code, 302)

    def test_detalle_categoria_retorna_datos(self):
        """GET al endpoint de detalle devuelve los datos de la categoría."""
        response = self.client.get(
            reverse('panel_admin:categoria_detalle', args=[self.categoria.pk])
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['nombre'], 'ServiciosTest')
        self.assertEqual(data['tipo'], 'EGRESO')


class ToggleCategoriaTestCase(CategoriasSetupMixin, TestCase):
    """CU-11: Desactivación/Reactivación de categorías."""

    def setUp(self):
        self.client = Client()
        self.admin = self._crear_admin()
        self.client.login(email='admin@test.com', password='admin1234!')
        self.categoria = Categoria.objects.create(
            nombre='TransporteTest', tipo='EGRESO', activo=True
        )

    def test_desactivar_categoria_activa(self):
        """Toggle sobre categoría activa la desactiva correctamente."""
        response = self.client.post(
            reverse('panel_admin:toggle_categoria', args=[self.categoria.pk])
        )
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertFalse(data['activo'])
        self.categoria.refresh_from_db()
        self.assertFalse(self.categoria.activo)

    def test_reactivar_categoria_inactiva(self):
        """Toggle sobre categoría inactiva la reactiva correctamente."""
        self.categoria.activo = False
        self.categoria.save()
        response = self.client.post(
            reverse('panel_admin:toggle_categoria', args=[self.categoria.pk])
        )
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['activo'])

    def test_toggle_sin_permiso_redirige(self):
        """Usuario no-admin no puede hacer toggle de categoría."""
        self.client.logout()
        self._crear_user_normal()
        self.client.login(email='user@test.com', password='user1234!')
        response = self.client.post(
            reverse('panel_admin:toggle_categoria', args=[self.categoria.pk])
        )
        self.assertEqual(response.status_code, 302)

    def test_toggle_metodo_get_falla(self):
        """GET al endpoint de toggle retorna 405."""
        response = self.client.get(
            reverse('panel_admin:toggle_categoria', args=[self.categoria.pk])
        )
        self.assertEqual(response.status_code, 405)
