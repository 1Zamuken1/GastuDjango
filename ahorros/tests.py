from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from .models import AhorroMeta, AporteAhorro
from categorias.models import Categoria
from datetime import date, timedelta
from usuarios.models import Usuario
from dashboard.models import ResumenMensual
from unittest.mock import patch
import datetime


class AhorrosViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = Usuario.objects.create_user(
            email='test@example.com',
            password='testpass123',
            username='testuser'
        )
        self.client.login(email='test@example.com', password='testpass123')

        # simulo(creo) la categoria de ahorro a usar
        self.categoria = Categoria.objects.create(
            nombre='Ahorro Test',
            tipo='AHORRO',
            activo=True
        )

        # simulo(creo) el ahorro a usar
        # frecuencia en MAYÚSCULAS para coincidir con las choices del modelo.
        self.ahorro = AhorroMeta.objects.create(
            usuario=self.user,
            categoria=self.categoria,
            monto_meta=Decimal('1000.00'),
            frecuencia='MENSUAL',
            fecha_meta=date.today() + timedelta(days=30),
            cantidad_cuotas=3,
            estado=AhorroMeta.Estado.SIN_INICIAR,
            total_acumulado=Decimal('0.00')
        )

    # ── LISTAR ─────────────────────────────────────────────────────────────

    def test_listar_ahorros(self):
        """Test the listar ahorros view"""
        response = self.client.get(reverse('ahorros:listar_ahorros'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ahorros/lista.html')
        self.assertContains(response, 'Ahorro Test')

    # ── CREAR ──────────────────────────────────────────────────────────────

    def test_crear_ahorro_get(self):
        """Test the crear ahorro view GET request"""
        response = self.client.get(reverse('ahorros:crear_ahorro'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ahorros/crear.html')

    def test_crear_ahorro_post(self):
        """Test the crear ahorro view POST request"""
        data = {
            'categoria': self.categoria.id,
            'monto_meta': '500.00',
            'frecuencia': 'MENSUAL',
            'fecha_meta': '',
            'cantidad_cuotas': '3',
            'descripcion': 'Ahorro creado correctamente'
        }
        response = self.client.post(reverse('ahorros:crear_ahorro'), data)
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.content}")

        if response.status_code == 200:
            print(response.context['form'].errors)
        # La vista redirige (302) en éxito o devuelve 200 con errores de form
        self.assertIn(response.status_code, [200, 302])
        self.assertTrue(AhorroMeta.objects.filter(descripcion='Ahorro creado correctamente').exists())

    # ── EDITAR ─────────────────────────────────────────────────────────────

    def test_editar_ahorro_get(self):
        response = self.client.get(reverse('ahorros:editar_ahorro', args=[self.ahorro.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ahorros/editar.html')

    def test_editar_ahorro_post(self):
        """Test que la petición POST realmente edite los datos de la meta de ahorro"""
        data = {
            'categoria': self.categoria.id,
            'monto_meta': '2000.00',
            'frecuencia': 'MENSUAL',
            'fecha_meta': '',
            'cantidad_cuotas': '6',
            'descripcion': 'Meta de ahorro modificada'
        }

        response = self.client.post(
            reverse('ahorros:editar_ahorro', args=[self.ahorro.id]),
            data
        )

        self.assertRedirects(response, reverse('ahorros:listar_ahorros'))
        self.ahorro.refresh_from_db()

        self.assertEqual(self.ahorro.monto_meta, Decimal('2000.00'))
        self.assertEqual(self.ahorro.cantidad_cuotas, 6)
        self.assertEqual(self.ahorro.descripcion, 'Meta de ahorro modificada')

    # ── ELIMINAR ───────────────────────────────────────────────────────────

    def test_eliminar_ahorro_get(self):
        """Test the eliminar ahorro view GET request"""
        response = self.client.get(reverse('ahorros:eliminar_ahorro', args=[self.ahorro.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ahorros/eliminar.html')

    def test_eliminar_ahorro_post(self):
        """Test que la peticion POST elimine la meta de ahorro"""
        response = self.client.post(reverse('ahorros:eliminar_ahorro', args=[self.ahorro.id]))
        self.assertRedirects(response, reverse('ahorros:listar_ahorros'))
        self.assertFalse(AhorroMeta.objects.filter(id=self.ahorro.id).exists())

    # ── REGISTRAR APORTE ───────────────────────────────────────────────────

    def test_registrar_aporte_get(self):
        """Test the registrar aporte view GET request"""
        AporteAhorro.objects.create(
            ahorro=self.ahorro,
            fecha_limite=date.today() + timedelta(days=30),
            aporte_asignado=Decimal('300.00'),
            estado_ap=AporteAhorro.EstadoAp.PENDIENTE,
            es_extraordinario=False,
        )

        response = self.client.get(reverse('ahorros:registrar_aporte', args=[self.ahorro.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ahorros/aporte.html')

    def test_registrar_aporte_post(self):
        """
        Test registrar un aporte mediante POST.

        Mocks usados:
        - obtener_disponible → la vista lo usa para validar saldo antes de aportar.
          Se mockea porque en tests no hay ingresos/gastos reales en el ResumenMensual
          y la función real devolvería 0, bloqueando el aporte.

        - actualizar_resumen (signal) → el signal historial_aporte_registrado llama
          actualizar_resumen() al final, que recalcula el ResumenMensual desde cero
          basándose en transacciones reales (que no existen en el test). Sin el mock
          sobreescribe disponible=1000 con el valor calculado (0 - 300 = -300).
          Se mockea para aislar la vista del efecto secundario del signal.
        """
        hoy = datetime.date.today()

        resumen = ResumenMensual.objects.create(
            usuario=self.user,
            mes=hoy.month,
            anio=hoy.year,
            disponible=Decimal('1000.00'),
            total_ahorros=Decimal('0.00')
        )

        # fecha_limite=hoy → no cae en pasar_cuotas_a_perdidas (filtro __lt)
        # es_extraordinario=False → la vista lo trata como cuota regular
        aporte = AporteAhorro.objects.create(
            ahorro=self.ahorro,
            fecha_limite=hoy,
            aporte_asignado=Decimal('300.00'),
            estado_ap=AporteAhorro.EstadoAp.PENDIENTE,
            es_extraordinario=False,
        )

        data = {'aporte': '300.00', 'aporte_id': aporte.id}

        with patch('dashboard.services.obtener_disponible', return_value=Decimal('1000.00')), \
            patch('dashboard.services.actualizar_resumen'):
            response = self.client.post(
                reverse('ahorros:registrar_aporte', args=[self.ahorro.id]),
                data
                )

        # ── Verificar respuesta ─────────────────────────────────────────────
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('ok'), response.json())

        # ── Verificar impacto en modelos ────────────────────────────────────
        aporte.refresh_from_db()
        self.ahorro.refresh_from_db()
        resumen.refresh_from_db()

        # La cuota debe quedar marcada como APORTADO
        self.assertEqual(aporte.estado_ap, AporteAhorro.EstadoAp.APORTADO)

        # El acumulado de la meta debe reflejar el aporte registrado
        self.assertEqual(self.ahorro.total_acumulado, Decimal('300.00'))

        # El resumen no fue tocado por actualizar_resumen (estaba mockeado),
        # así que disponible permanece en el valor que pusimos al crearlo.
        self.assertEqual(resumen.disponible, Decimal('1000.00'))