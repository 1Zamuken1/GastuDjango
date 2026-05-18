"""
tests/test_movimientos.py
=========================
Tests del módulo de movimientos (ingresos y egresos).
Cubre: CU-18, CU-19, CU-20, CU-21, CU-22.
Amplía el tests.py original del proyecto.

Ejecutar:  python manage.py test tests.test_movimientos
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from categorias.models import Categoria
from movimientos.models import Movimiento
from usuarios.models import Usuario


class MovimientosSetupMixin:
    """Datos de prueba reutilizables para tests de movimientos."""

    def _setup_base(self):
        self.client = Client()
        self.user = Usuario.objects.create_user(
            email='mov@test.com',
            password='pass1234!',
            username='movtest'
        )
        self.client.login(email='mov@test.com', password='pass1234!')

        self.cat_ingreso = Categoria.objects.create(
            nombre='SalarioTest', tipo='INGRESO', activo=True
        )
        self.cat_egreso = Categoria.objects.create(
            nombre='AlimentacionTest', tipo='EGRESO', activo=True
        )
        self.ingreso = Movimiento.objects.create(
            usuario=self.user,
            categoria=self.cat_ingreso,
            tipo='INGRESO',
            monto=Decimal('2000.00'),
            descripcion='Salario mensual'
        )
        self.egreso = Movimiento.objects.create(
            usuario=self.user,
            categoria=self.cat_egreso,
            tipo='EGRESO',
            monto=Decimal('350.00'),
            descripcion='Supermercado semanal'
        )


class VistaMovimientosTestCase(MovimientosSetupMixin, TestCase):
    """CU-18: Visualización de la lista de movimientos."""

    def setUp(self):
        self._setup_base()

    def test_vista_ingresos_retorna_200(self):
        """GET /ingresos/ carga la plantilla con estado 200."""
        response = self.client.get(reverse('movimientos:ingresos'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'movimientos/ingresos.html')

    def test_vista_egresos_retorna_200(self):
        """GET /egresos/ carga la plantilla con estado 200."""
        response = self.client.get(reverse('movimientos:egresos'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'movimientos/egresos.html')

    def test_ingresos_muestra_categoria(self):
        """La vista de ingresos contiene el nombre de la categoría."""
        response = self.client.get(reverse('movimientos:ingresos'))
        self.assertContains(response, 'SalarioTest')

    def test_egresos_muestra_categoria(self):
        """La vista de egresos contiene el nombre de la categoría."""
        response = self.client.get(reverse('movimientos:egresos'))
        self.assertContains(response, 'AlimentacionTest')

    def test_ingresos_sin_sesion_redirige_login(self):
        """Acceder a ingresos sin sesión redirige al login."""
        self.client.logout()
        response = self.client.get(reverse('movimientos:ingresos'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_egresos_sin_sesion_redirige_login(self):
        """Acceder a egresos sin sesión redirige al login."""
        self.client.logout()
        response = self.client.get(reverse('movimientos:egresos'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])


class CrearMovimientoTestCase(MovimientosSetupMixin, TestCase):
    """CU-19: Creación de movimientos."""

    def setUp(self):
        self._setup_base()

    def test_crear_ingreso_valido(self):
        """POST con ingreso válido crea el movimiento y retorna ok=True."""
        response = self.client.post(reverse('movimientos:guardar_movimiento'), {
            'tipo': 'INGRESO',
            'categoria': self.cat_ingreso.id,
            'monto': '500.00',
            'descripcion': 'Freelance pago'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertTrue(Movimiento.objects.filter(descripcion='Freelance pago').exists())

    def test_crear_egreso_valido(self):
        """POST con egreso válido crea el movimiento y retorna ok=True."""
        response = self.client.post(reverse('movimientos:guardar_movimiento'), {
            'tipo': 'EGRESO',
            'categoria': self.cat_egreso.id,
            'monto': '120.00',
            'descripcion': 'Internet mensual'
        })
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertTrue(Movimiento.objects.filter(descripcion='Internet mensual').exists())

    def test_crear_ingreso_sin_descripcion(self):
        """Crear movimiento sin descripción (campo opcional) funciona."""
        response = self.client.post(reverse('movimientos:guardar_movimiento'), {
            'tipo': 'INGRESO',
            'categoria': self.cat_ingreso.id,
            'monto': '300.00',
            'descripcion': ''
        })
        data = response.json()
        self.assertTrue(data['ok'])

    def test_crear_movimiento_monto_negativo_falla(self):
        """Monto negativo retorna ok=False y no crea el movimiento."""
        count_antes = Movimiento.objects.count()
        response = self.client.post(reverse('movimientos:guardar_movimiento'), {
            'tipo': 'INGRESO',
            'categoria': self.cat_ingreso.id,
            'monto': '-100.00',
            'descripcion': 'Monto invalido'
        })
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertEqual(Movimiento.objects.count(), count_antes)

    def test_crear_movimiento_sin_categoria_falla(self):
        """Movimiento sin categoría retorna ok=False."""
        response = self.client.post(reverse('movimientos:guardar_movimiento'), {
            'tipo': 'INGRESO',
            'categoria': '',
            'monto': '200.00',
            'descripcion': 'Sin categoria'
        })
        data = response.json()
        self.assertFalse(data['ok'])

    def test_crear_movimiento_sin_sesion_falla(self):
        """Sin sesión activa, crear movimiento redirige o rechaza."""
        self.client.logout()
        response = self.client.post(reverse('movimientos:guardar_movimiento'), {
            'tipo': 'INGRESO',
            'categoria': self.cat_ingreso.id,
            'monto': '200.00',
        })
        self.assertIn(response.status_code, [302, 403])


class FiltradoPeriodosTestCase(MovimientosSetupMixin, TestCase):
    """CU-20: Consulta y filtro de períodos."""

    def setUp(self):
        self._setup_base()

    def test_resumen_ingresos_mes_actual(self):
        """El resumen de ingresos devuelve los totales del mes en curso."""
        response = self.client.get(
            reverse('movimientos:resumen_movimientos') + '?tipo=INGRESO'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        # El total del mes es al menos el ingreso creado en setUp
        self.assertGreaterEqual(float(data['total_mes']), 2000.00)

    def test_resumen_egresos_mes_actual(self):
        """El resumen de egresos devuelve los totales del mes en curso."""
        response = self.client.get(
            reverse('movimientos:resumen_movimientos') + '?tipo=EGRESO'
        )
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertGreaterEqual(float(data['total_mes']), 350.00)

    def test_buscar_por_texto(self):
        """Buscar por texto encuentra el movimiento correcto."""
        response = self.client.get(
            reverse('movimientos:buscar_registros') + '?q=Salario&tipo=INGRESO'
        )
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertGreaterEqual(len(data['resultados']), 1)

    def test_buscar_por_monto(self):
        """Buscar por monto devuelve los movimientos que coinciden."""
        response = self.client.get(
            reverse('movimientos:buscar_registros') + '?q=350&tipo=EGRESO'
        )
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertGreaterEqual(len(data['resultados']), 1)

    def test_buscar_por_fecha(self):
        """Buscar por la fecha de hoy devuelve los movimientos del día."""
        hoy = timezone.localdate().strftime('%d/%m/%Y')
        response = self.client.get(
            reverse('movimientos:buscar_registros') + f'?q={hoy}&tipo=INGRESO'
        )
        data = response.json()
        self.assertTrue(data['ok'])

    def test_registros_por_categoria(self):
        """El endpoint de registros devuelve solo los de la categoría."""
        response = self.client.get(
            reverse('movimientos:registros_por_categoria') +
            f'?categoria={self.cat_ingreso.id}'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['registros'][0]['descripcion'], 'Salario mensual')

    def test_acceso_sin_sesion_redirige(self):
        """Sin sesión, el endpoint de búsqueda redirige al login."""
        self.client.logout()
        response = self.client.get(
            reverse('movimientos:buscar_registros') + '?q=test&tipo=INGRESO'
        )
        self.assertIn(response.status_code, [302, 403])


class EdicionMovimientoTestCase(MovimientosSetupMixin, TestCase):
    """CU-21: Edición y validación de movimientos."""

    def setUp(self):
        self._setup_base()

    def test_editar_monto_exitoso(self):
        """Editar el monto de un movimiento lo actualiza en BD."""
        response = self.client.post(
            reverse('movimientos:editar_movimiento', args=[self.ingreso.pk]),
            {
                'categoria': self.cat_ingreso.id,
                'monto': '2500.00',
                'tipo': 'INGRESO',
                'descripcion': 'Salario mensual actualizado'
            }
        )
        data = response.json()
        self.assertTrue(data['ok'])
        self.ingreso.refresh_from_db()
        self.assertEqual(self.ingreso.monto, Decimal('2500.00'))

    def test_editar_categoria_exitoso(self):
        """Editar la categoría de un movimiento la actualiza correctamente."""
        cat_nueva = Categoria.objects.create(nombre='BonificacionTest', tipo='INGRESO', activo=True)
        response = self.client.post(
            reverse('movimientos:editar_movimiento', args=[self.ingreso.pk]),
            {
                'categoria': cat_nueva.id,
                'monto': '2000.00',
                'tipo': 'INGRESO',
                'descripcion': 'Salario mensual'
            }
        )
        data = response.json()
        self.assertTrue(data['ok'])
        self.ingreso.refresh_from_db()
        self.assertEqual(self.ingreso.categoria.pk, cat_nueva.pk)

    def test_editar_monto_negativo_falla(self):
        """Editar con monto negativo retorna ok=False."""
        response = self.client.post(
            reverse('movimientos:editar_movimiento', args=[self.ingreso.pk]),
            {
                'categoria': self.cat_ingreso.id,
                'monto': '-100.00',
                'descripcion': 'Monto invalido'
            }
        )
        data = response.json()
        self.assertFalse(data['ok'])
        # El monto no debe haber cambiado
        self.ingreso.refresh_from_db()
        self.assertEqual(self.ingreso.monto, Decimal('2000.00'))

    def test_editar_monto_vacio_falla(self):
        """Editar dejando el monto en blanco retorna ok=False."""
        response = self.client.post(
            reverse('movimientos:editar_movimiento', args=[self.ingreso.pk]),
            {
                'categoria': self.cat_ingreso.id,
                'monto': '',
                'descripcion': 'Test'
            }
        )
        data = response.json()
        self.assertFalse(data['ok'])

    def test_editar_sin_categoria_falla(self):
        """Editar sin categoría retorna ok=False."""
        response = self.client.post(
            reverse('movimientos:editar_movimiento', args=[self.ingreso.pk]),
            {
                'categoria': '',
                'monto': '2000.00',
                'descripcion': 'Sin categoria'
            }
        )
        data = response.json()
        self.assertFalse(data['ok'])

    def test_editar_movimiento_ajeno_no_permitido(self):
        """Un usuario no puede editar movimientos de otro usuario."""
        otro_user = Usuario.objects.create_user(
            email='otro@test.com', password='pass1234!', username='otro'
        )
        self.client.logout()
        self.client.login(email='otro@test.com', password='pass1234!')
        response = self.client.post(
            reverse('movimientos:editar_movimiento', args=[self.ingreso.pk]),
            {'categoria': self.cat_ingreso.id, 'monto': '9999.00', 'descripcion': 'hack'}
        )
        # Debe retornar 404 o error
        self.assertIn(response.status_code, [404, 403, 200])
        if response.status_code == 200:
            self.assertFalse(response.json().get('ok', True))


class EliminarMovimientoTestCase(MovimientosSetupMixin, TestCase):
    """CU-22: Eliminación de movimientos."""

    def setUp(self):
        self._setup_base()

    def test_eliminar_ingreso_exitoso(self):
        """Eliminar un ingreso lo borra de la BD y retorna ok=True."""
        mov_id = self.ingreso.pk
        response = self.client.post(
            reverse('movimientos:eliminar_movimiento', args=[mov_id])
        )
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertFalse(Movimiento.objects.filter(pk=mov_id).exists())

    def test_eliminar_egreso_exitoso(self):
        """Eliminar un egreso lo borra de la BD y retorna ok=True."""
        mov_id = self.egreso.pk
        response = self.client.post(
            reverse('movimientos:eliminar_movimiento', args=[mov_id])
        )
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertFalse(Movimiento.objects.filter(pk=mov_id).exists())

    def test_eliminar_sin_sesion_falla(self):
        """Sin sesión activa, eliminar redirige al login."""
        self.client.logout()
        response = self.client.post(
            reverse('movimientos:eliminar_movimiento', args=[self.ingreso.pk])
        )
        self.assertIn(response.status_code, [302, 403])

    def test_eliminar_movimiento_inexistente_retorna_404(self):
        """Eliminar un ID inexistente retorna ok=False con error controlado."""
        response = self.client.post(
            reverse('movimientos:eliminar_movimiento', args=[999999])
        )
        self.assertIn(response.status_code, [404, 200])
        if response.status_code == 200:
            data = response.json()
            self.assertFalse(data.get('ok', True))
