"""Tests del pool de avatares."""
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse

from usuarios.models import Usuario
from usuarios.services import AVATARES, avatar_de, cambiar_avatar


class PoolAvataresTestCase(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='ana', email='ana@example.com', password='ClaveSegura123!'
        )

    def test_sin_avatar_usa_la_inicial(self):
        avatar = avatar_de(self.usuario)
        self.assertEqual(avatar['tipo'], 'inicial')
        self.assertEqual(avatar['inicial'], 'A')

    def test_cambiar_avatar_valido(self):
        avatar = cambiar_avatar(self.usuario, 'gato')
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.avatar, 'gato')
        self.assertEqual(avatar['tipo'], 'pool')
        self.assertEqual(avatar['icono'], AVATARES['gato']['icono'])

    def test_cambiar_avatar_invalido_lanza_error(self):
        with self.assertRaises(ValueError):
            cambiar_avatar(self.usuario, '<script>')
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.avatar, '')

    def test_volver_a_automatico(self):
        cambiar_avatar(self.usuario, 'sol')
        avatar = cambiar_avatar(self.usuario, '')
        self.assertEqual(avatar['tipo'], 'inicial')

    def test_clave_guardada_que_ya_no_existe_cae_a_automatico(self):
        Usuario.objects.filter(pk=self.usuario.pk).update(avatar='dragon')
        self.usuario.refresh_from_db()
        self.assertEqual(avatar_de(self.usuario)['tipo'], 'inicial')

    def test_etiqueta_pinta_icono_del_pool(self):
        cambiar_avatar(self.usuario, 'cohete')
        html = Template(
            '{% load usuarios_extras %}{% avatar_usuario u "user-avatar" %}'
        ).render(Context({'u': self.usuario}))
        self.assertIn('data-avatar-slot', html)
        self.assertIn('data-lucide="rocket"', html)
        self.assertIn('avatar-ui--pool', html)


class CambiarAvatarVistaTestCase(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='beto', email='beto@example.com', password='ClaveSegura123!'
        )
        self.url = reverse('cambiar_avatar')

    def test_requiere_sesion(self):
        resp = self.client.post(self.url, {'avatar': 'gato'})
        self.assertEqual(resp.status_code, 302)

    def test_solo_post(self):
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_post_valido_guarda_y_responde(self):
        self.client.force_login(self.usuario)
        resp = self.client.post(self.url, {'avatar': 'pez'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['avatar']['clave'], 'pez')
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.avatar, 'pez')

    def test_post_invalido_responde_400(self):
        self.client.force_login(self.usuario)
        resp = self.client.post(self.url, {'avatar': 'no-existe'})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()['ok'])

    def test_perfil_muestra_selector_y_avatar(self):
        cambiar_avatar(self.usuario, 'hoja')
        self.client.force_login(self.usuario)
        resp = self.client.get(reverse('perfil'))
        self.assertContains(resp, 'id="modal-avatar"')
        self.assertContains(resp, 'data-lucide="leaf"')
        # Una opcion por avatar del pool mas la de Automatico
        self.assertContains(resp, 'role="radio"', count=len(AVATARES) + 1)
