"""
tests/test_notificaciones.py
============================
Tests del módulo de notificaciones (CU-46).
Cubre: marcar leída, marcar todas, endpoint JSON,
       acceso no autenticado, ID inexistente.

Ejecutar:  python manage.py test tests.test_notificaciones
"""
from django.test import TestCase, Client
from django.urls import reverse
from notificaciones.models import Notificacion
from usuarios.models import Usuario


class NotificacionesSetupMixin:
    """Datos comunes para tests de notificaciones."""

    def _setup_base(self):
        self.client = Client()
        self.user = Usuario.objects.create_user(
            email='notif@test.com',
            password='pass1234!',
            username='notiftest'
        )
        self.client.login(email='notif@test.com', password='pass1234!')

        # Crear 3 notificaciones no leídas
        self.notif1 = Notificacion.objects.create(
            usuario=self.user,
            tipo=Notificacion.Tipo.DEFICIT,
            titulo='Balance en déficit',
            descripcion='Tu balance está en déficit.',
            modulo=Notificacion.Modulo.GENERAL,
            leida=False
        )
        self.notif2 = Notificacion.objects.create(
            usuario=self.user,
            tipo=Notificacion.Tipo.EGRESO_GRANDE,
            titulo='Egreso grande',
            descripcion='Registraste un egreso alto.',
            modulo=Notificacion.Modulo.EGRESOS,
            leida=False
        )
        self.notif3 = Notificacion.objects.create(
            usuario=self.user,
            tipo=Notificacion.Tipo.UMBRAL_MENSUAL,
            titulo='Umbral alcanzado',
            descripcion='Has llegado al 90% del presupuesto.',
            modulo=Notificacion.Modulo.PRESUPUESTOS,
            leida=False
        )


class ListadoNotificacionesTestCase(NotificacionesSetupMixin, TestCase):
    """Pruebas del endpoint JSON de notificaciones."""

    def setUp(self):
        self._setup_base()

    def test_endpoint_json_retorna_200(self):
        """GET /notificaciones/json/ retorna 200 y estructura correcta."""
        response = self.client.get(reverse('notificaciones_json'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertIn('notificaciones', data)
        self.assertIn('total_no_leidas', data)

    def test_endpoint_json_retorna_no_leidas(self):
        """El JSON indica el total correcto de notificaciones no leídas."""
        response = self.client.get(reverse('notificaciones_json'))
        data = response.json()
        self.assertEqual(data['total_no_leidas'], 3)

    def test_endpoint_json_incluye_recuentos_modulos(self):
        """El JSON incluye el campo de recuentos por módulo."""
        response = self.client.get(reverse('notificaciones_json'))
        data = response.json()
        self.assertIn('recuentos_modulos', data)
        self.assertIsInstance(data['recuentos_modulos'], dict)

    def test_endpoint_json_sin_sesion_redirige(self):
        """Sin sesión, el endpoint JSON redirige al login."""
        self.client.logout()
        response = self.client.get(reverse('notificaciones_json'))
        self.assertIn(response.status_code, [302, 403])

    def test_filtro_por_modulo(self):
        """Filtrar por módulo devuelve solo las notificaciones de ese módulo."""
        response = self.client.get(
            reverse('notificaciones_json') + '?modulo=EGRESOS'
        )
        data = response.json()
        self.assertTrue(data['ok'])
        for notif in data['notificaciones']:
            self.assertEqual(notif['modulo'], 'EGRESOS')


class MarcarLeidaTestCase(NotificacionesSetupMixin, TestCase):
    """CU-46: Marcar notificación individual como leída."""

    def setUp(self):
        self._setup_base()

    def _get_csrf(self):
        """Obtiene el CSRF token de la sesión actual."""
        self.client.get(reverse('perfil'))
        return self.client.cookies.get('csrftoken').value if self.client.cookies.get('csrftoken') else ''

    def test_marcar_una_leida_exitoso(self):
        """Marcar un ID específico lo pone en leída=True."""
        import json
        response = self.client.post(
            reverse('notificaciones_marcar_leidas'),
            data=json.dumps({'ids': [self.notif1.pk]}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['afectadas'], 1)
        self.notif1.refresh_from_db()
        self.assertTrue(self.notif1.leida)

    def test_marcar_una_leida_reduce_contador(self):
        """Marcar una como leída reduce el total de no leídas."""
        import json
        self.client.post(
            reverse('notificaciones_marcar_leidas'),
            data=json.dumps({'ids': [self.notif1.pk]}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        no_leidas = Notificacion.objects.filter(usuario=self.user, leida=False).count()
        self.assertEqual(no_leidas, 2)

    def test_marcar_id_inexistente_retorna_cero_afectadas(self):
        """Marcar un ID inexistente retorna ok=True con afectadas=0 (sin crash)."""
        import json
        response = self.client.post(
            reverse('notificaciones_marcar_leidas'),
            data=json.dumps({'ids': [999999]}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['afectadas'], 0)

    def test_marcar_sin_sesion_redirige(self):
        """Sin sesión, marcar como leída redirige al login."""
        import json
        self.client.logout()
        response = self.client.post(
            reverse('notificaciones_marcar_leidas'),
            data=json.dumps({'ids': [self.notif1.pk]}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertIn(response.status_code, [302, 403])


class MarcarTodasLeidasTestCase(NotificacionesSetupMixin, TestCase):
    """CU-46: Marcar todas las notificaciones como leídas."""

    def setUp(self):
        self._setup_base()

    def test_marcar_todas_exitoso(self):
        """POST sin IDs marca todas las notificaciones del usuario como leídas."""
        import json
        response = self.client.post(
            reverse('notificaciones_marcar_leidas'),
            data=json.dumps({}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        # Todas deben estar leídas ahora
        no_leidas = Notificacion.objects.filter(usuario=self.user, leida=False).count()
        self.assertEqual(no_leidas, 0)

    def test_marcar_todas_afecta_solo_al_usuario(self):
        """Marcar todas solo cambia las notificaciones del usuario en sesión."""
        import json
        otro = Usuario.objects.create_user(
            email='otro@test.com', password='pass1234!', username='otro'
        )
        notif_otro = Notificacion.objects.create(
            usuario=otro,
            tipo=Notificacion.Tipo.DEFICIT,
            titulo='Alerta otro',
            descripcion='Descripcion',
            leida=False
        )
        self.client.post(
            reverse('notificaciones_marcar_leidas'),
            data=json.dumps({}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        # La notificación del otro usuario no debe haber cambiado
        notif_otro.refresh_from_db()
        self.assertFalse(notif_otro.leida)


class PerfilNotificacionesTestCase(TestCase):
    """Prueba de acceso al perfil con tab de notificaciones."""

    def setUp(self):
        self.client = Client()
        self.user = Usuario.objects.create_user(
            email='perfilnotif@test.com',
            password='pass1234!',
            username='perfilnotif'
        )

    def test_perfil_notificaciones_sin_sesion_redirige(self):
        """Acceder a /perfil/?tab=notificaciones sin sesión redirige al login."""
        response = self.client.get(reverse('perfil') + '?tab=notificaciones')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_perfil_notificaciones_con_sesion_retorna_200(self):
        """Acceder a /perfil/?tab=notificaciones con sesión retorna 200."""
        self.client.login(email='perfilnotif@test.com', password='pass1234!')
        response = self.client.get(reverse('perfil') + '?tab=notificaciones')
        self.assertEqual(response.status_code, 200)
