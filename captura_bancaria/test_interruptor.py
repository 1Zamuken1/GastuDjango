"""Tests del interruptor CAPTURA_HABILITADA."""
from django.test import TestCase, override_settings
from django.urls import reverse

from usuarios.models import Usuario

RUTAS_GET = ['captura', 'api_buzon', 'api_resumen', 'api_detectados', 'api_reglas']


class InterruptorCapturaTestCase(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='caro', email='caro@example.com', password='ClaveSegura123!'
        )
        self.client.force_login(self.usuario)

    @override_settings(CAPTURA_HABILITADA=False)
    def test_apagada_todas_las_rutas_responden_404(self):
        for nombre in RUTAS_GET:
            resp = self.client.get(reverse(f'captura_bancaria:{nombre}'))
            self.assertEqual(resp.status_code, 404, nombre)

    @override_settings(CAPTURA_HABILITADA=False)
    def test_apagada_la_ingesta_de_correos_responde_404(self):
        self.client.logout()
        resp = self.client.post(reverse('captura_bancaria:ingesta'), data=b'x', content_type='message/rfc822')
        self.assertEqual(resp.status_code, 404)

    @override_settings(CAPTURA_HABILITADA=False)
    def test_apagada_no_aparece_en_menu_ni_panel(self):
        resp = self.client.get(reverse('dashboard:home'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'Captura automática')
        self.assertNotContains(resp, 'id="notif-pendientes"')
        self.assertNotContains(resp, 'panel_pendientes.js')
        self.assertContains(resp, 'data-captura="0"')

    @override_settings(CAPTURA_HABILITADA=True)
    def test_encendida_funciona_como_siempre(self):
        self.assertEqual(self.client.get(reverse('captura_bancaria:captura')).status_code, 200)
        resp = self.client.get(reverse('dashboard:home'))
        self.assertContains(resp, 'Captura automática')
        self.assertContains(resp, 'id="notif-pendientes"')
        self.assertContains(resp, 'data-captura="1"')
