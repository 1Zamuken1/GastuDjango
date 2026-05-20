from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal
from .models import AhorroMeta, AporteAhorro
from categorias.models import Categoria
from datetime import date, timedelta
from usuarios.models import Usuario
from dashboard.models import ResumenMensual
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
        
        # simulo(creo) la categoia de ahorro a usar
        self.categoria = Categoria.objects.create(
            nombre='Ahorro Test',
            tipo='AHORRO',
            activo=True
        )
        
        # simulo(creo) el ahorro a usar
        self.ahorro = AhorroMeta.objects.create(
            usuario=self.user,
            categoria=self.categoria,
            monto_meta=Decimal('1000.00'),
            frecuencia='mensual',
            fecha_meta=date.today() + timedelta(days=30),
            cantidad_cuotas=3,
            estado=AhorroMeta.Estado.SIN_INICIAR,
            total_acumulado=Decimal('0.00')
        )

    def test_listar_ahorros(self):
        """Test the listar ahorros view"""
        response = self.client.get(reverse('ahorros:listar_ahorros'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ahorros/lista.html')
        self.assertContains(response, 'Ahorro Test')

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
        # Imprimir detalles de la respuesta para depuración
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.content}")
        # puede devolver 200 o 302(redireccionamiento)
    
        if response.status_code == 200:
            print(response.context['form'].errors)
        self.assertIn(response.status_code, [200, 302])
        self.assertTrue(AhorroMeta.objects.filter(descripcion='Ahorro creado correctamente').exists())

    def test_editar_ahorro_get(self):
        response = self.client.get(reverse('ahorros:editar_ahorro', args=[self.ahorro.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ahorros/editar.html')
    
    def test_editar_ahorro_post(self):
        """Test que la petición POST realmente edite los datos de la meta de ahorro"""
        #Definimos los nuevos datos para modificar el ahorro existente
        data = {
            'categoria': self.categoria.id,
            'monto_meta': '2000.00',        # Cambiamos de 1000.00 a 2000.00
            'frecuencia': 'MENSUAL',
            'fecha_meta': '',
            'cantidad_cuotas': '6',         # Cambiamos de 3 a 6 cuotas
            'descripcion': 'Meta de ahorro modificada'
        }
        
        # Ejecutamos la petición POST hacia la vista de editar
        response = self.client.post(
            reverse('ahorros:editar_ahorro', args=[self.ahorro.id]), 
            data
        )
        
        #view redirige tras tener éxito
        self.assertRedirects(response, reverse('ahorros:listar_ahorros'))
        #Traemos el objeto actualizado directamente desde la Base de Datos
        self.ahorro.refresh_from_db()
        
        #Comprobamos que los cambios se hayan aplicado de verdad
        self.assertEqual(self.ahorro.monto_meta, Decimal('2000.00'))
        self.assertEqual(self.ahorro.cantidad_cuotas, 6)
        self.assertEqual(self.ahorro.descripcion, 'Meta de ahorro modificada')

    def test_eliminar_ahorro_get(self):
        """Test the eliminar ahorro view GET request"""
        response = self.client.get(reverse('ahorros:eliminar_ahorro', args=[self.ahorro.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ahorros/eliminar.html')
        
    def test_eliminar_ahorro_post(self):
       """Test que la peticion POST elimine la meta de ahorro"""
       response = self.client.post(reverse('ahorros:eliminar_ahorro', args=[self.ahorro.id]))
       self.assertRedirects(response, reverse('ahorros:listar_ahorros'))
       # Verificamos que ya NO exista en la base de datos
       self.assertFalse(AhorroMeta.objects.filter(id=self.ahorro.id).exists())

    def test_registrar_aporte_get(self):
        """Test the registrar aporte view GET request"""
        # First create an aporte for testing
        aporte = AporteAhorro.objects.create(
            ahorro=self.ahorro,
            fecha_limite=date.today() + timedelta(days=30),
            aporte_asignado=Decimal('300.00'),
            estado_ap=AporteAhorro.EstadoAp.PENDIENTE
        )
        
        response = self.client.get(reverse('ahorros:registrar_aporte', args=[self.ahorro.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ahorros/aporte.html')
        
    def test_registrar_aporte_post(self):
        """Test registrar un aporte mediante POST actualizando el saldo disponible"""
        # Crear el escenario necesario en la BD simulada
        hoy = datetime.date.today()
        resumen = ResumenMensual.objects.create(
            usuario=self.user,
            mes=hoy.month,
            anio=hoy.year,
            disponible=Decimal('1000.00'),
            total_ahorros=Decimal('0.00')
        )
        
        aporte = AporteAhorro.objects.create(
            ahorro=self.ahorro,
            fecha_limite=hoy,
            aporte_asignado=Decimal('300.00'),
            estado_ap=AporteAhorro.EstadoAp.PENDIENTE
        )

        # Ejecutar la peticion POST enviando el valor del aporte
        data = {
            'aporte': '300.00',
            'aporte_id': aporte.id
        }
        response = self.client.post(reverse('ahorros:registrar_aporte', args=[self.ahorro.id]), data)
        
        # Verificar la respuesta JSON que retorna tu vista
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        
        # Verificar que impactó correctamente tus modelos reales
        aporte.refresh_from_db()
        resumen.refresh_from_db()
        self.ahorro.refresh_from_db()
        
        self.assertEqual(aporte.estado_ap, AporteAhorro.EstadoAp.APORTADO)
        self.assertEqual(resumen.disponible, Decimal('700.00'))  # 1000 - 300
        self.assertEqual(self.ahorro.total_acumulado, Decimal('300.00'))