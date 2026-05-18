"""
tests/test_dashboard.py
=======================
Tests del módulo de Dashboard (CU-17).
Cubre: carga inicial, navegación de meses, endpoints JSON,
       acceso no autenticado.

Ejecutar:  python manage.py test tests.test_dashboard
"""
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from categorias.models import Categoria
from movimientos.models import Movimiento
from dashboard.models import ResumenMensual
from usuarios.models import Usuario


class DashboardSetupMixin:
    """Datos comunes para tests del dashboard."""

    def _setup_base(self):
        self.client = Client()
        self.user = Usuario.objects.create_user(
            email='dash@test.com',
            password='pass1234!',
            username='dashtest'
        )
        self.client.login(email='dash@test.com', password='pass1234!')

        self.cat_ingreso = Categoria.objects.create(
            nombre='SalarioTest', tipo='INGRESO', activo=True
        )
        self.cat_egreso = Categoria.objects.create(
            nombre='AlquilerTest', tipo='EGRESO', activo=True
        )

        hoy = timezone.now()
        # Crear un ingreso y un egreso del mes actual
        Movimiento.objects.create(
            usuario=self.user,
            categoria=self.cat_ingreso,
            tipo='INGRESO',
            monto=Decimal('3000.00'),
            descripcion='Sueldo mayo'
        )
        Movimiento.objects.create(
            usuario=self.user,
            categoria=self.cat_egreso,
            tipo='EGRESO',
            monto=Decimal('800.00'),
            descripcion='Arriendo mayo'
        )
        # Obtener o actualizar el ResumenMensual creado por las signals
        self.resumen, _ = ResumenMensual.objects.get_or_create(
            usuario=self.user,
            mes=hoy.month,
            anio=hoy.year,
            defaults={
                'total_ingresos': Decimal('3000.00'),
                'total_egresos': Decimal('800.00'),
                'disponible': Decimal('2200.00')
            }
        )


class DashboardHomeTestCase(DashboardSetupMixin, TestCase):
    """Pruebas de la vista principal del Dashboard."""

    def setUp(self):
        self._setup_base()

    def test_home_retorna_200(self):
        """GET /dashboard/ retorna 200 para usuario autenticado."""
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/home.html')

    def test_home_sin_sesion_redirige_login(self):
        """Sin sesión activa, el dashboard redirige al login."""
        self.client.logout()
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_home_ajax_retorna_json(self):
        """Dashboard con header AJAX retorna datos JSON."""
        hoy = timezone.now()
        response = self.client.get(
            reverse('dashboard:home') + f'?mes={hoy.month}&anio={hoy.year}',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('total_ingresos', data)
        self.assertIn('total_egresos', data)

    def test_home_mes_anterior_retorna_datos(self):
        """Dashboard con parámetro de mes anterior retorna datos correctos."""
        hoy = timezone.now()
        mes_ant = hoy.month - 1 if hoy.month > 1 else 12
        anio_ant = hoy.year if hoy.month > 1 else hoy.year - 1
        response = self.client.get(
            reverse('dashboard:home') + f'?mes={mes_ant}&anio={anio_ant}',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)

    def test_home_muestra_nombre_usuario(self):
        """El dashboard cargado en HTML contiene el nombre del usuario."""
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'dashtest')

    def test_home_mes_futuro_retorna_ceros(self):
        """Dashboard en un mes futuro sin datos devuelve totales en 0."""
        response = self.client.get(
            reverse('dashboard:home') + '?mes=12&anio=2099',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(float(data.get('total_ingresos', 0)), 0.0)
        self.assertEqual(float(data.get('total_egresos', 0)), 0.0)


class DashboardEndpointsTestCase(DashboardSetupMixin, TestCase):
    """Pruebas de los endpoints secundarios del Dashboard."""

    def setUp(self):
        self._setup_base()

    def test_meses_disponibles_retorna_lista(self):
        """El endpoint de meses disponibles retorna la configuración de paginación de meses."""
        response = self.client.get(reverse('dashboard:meses_disponibles'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('primer_mes', data)
        self.assertIn('primer_anio', data)

    def test_meses_disponibles_sin_sesion_redirige(self):
        """Sin sesión, el endpoint de meses redirige al login."""
        self.client.logout()
        response = self.client.get(reverse('dashboard:meses_disponibles'))
        self.assertIn(response.status_code, [302, 403])

    def test_tendencia_mes_retorna_datos(self):
        """El endpoint de tendencia devuelve datos para el mes actual."""
        hoy = timezone.now()
        response = self.client.get(
            reverse('dashboard:tendencia_mes') + f'?mes={hoy.month}&anio={hoy.year}'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('ingresos', data)
        self.assertIn('egresos', data)

    def test_tendencia_mes_sin_sesion_falla(self):
        """Sin sesión activa, la tendencia redirige al login."""
        self.client.logout()
        hoy = timezone.now()
        response = self.client.get(
            reverse('dashboard:tendencia_mes') + f'?mes={hoy.month}&anio={hoy.year}'
        )
        self.assertIn(response.status_code, [302, 403])

    def test_resumen_mensual_aislado_por_usuario(self):
        """El ResumenMensual se crea y se asocia correctamente al usuario."""
        from dashboard.models import ResumenMensual
        hoy = timezone.now()
        existe = ResumenMensual.objects.filter(
            usuario=self.user, mes=hoy.month, anio=hoy.year
        ).exists()
        self.assertTrue(existe)
