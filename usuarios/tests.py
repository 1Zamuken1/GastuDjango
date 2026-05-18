"""
tests/test_usuarios.py
======================
Tests del módulo de autenticación y perfil de usuario.
Cubre: login, logout, register, perfil, cambio de contraseña.

Ejecutar:  python manage.py test tests.test_usuarios
"""
from django.test import TestCase, Client
from django.urls import reverse
from usuarios.models import Usuario, Preferencias


class AutenticacionTestCase(TestCase):
    """Pruebas de login, logout y registro de usuario."""

    def setUp(self):
        self.client = Client()
        self.user = Usuario.objects.create_user(
            email='usuario@test.com',
            password='pass1234!',
            username='usuariotest'
        )

    # ── Login ────────────────────────────────────────────────────

    def test_login_exitoso_redirige_dashboard(self):
        """Login con credenciales válidas redirige al dashboard."""
        response = self.client.post(reverse('login'), {
            'email': 'usuario@test.com',
            'password': 'pass1234!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard/', response['Location'])

    def test_login_password_incorrecto(self):
        """Login con contraseña incorrecta permanece en el login."""
        response = self.client.post(reverse('login'), {
            'email': 'usuario@test.com',
            'password': 'wrongpassword',
        })
        # No redirige — sigue en la pantalla de login
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'usuarios/login.html')

    def test_login_email_inexistente(self):
        """Login con email que no existe permanece en el login."""
        response = self.client.post(reverse('login'), {
            'email': 'noexiste@test.com',
            'password': 'pass1234!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'usuarios/login.html')

    def test_login_campos_vacios(self):
        """Login sin rellenar email ni contraseña permanece en login."""
        response = self.client.post(reverse('login'), {
            'email': '',
            'password': '',
        })
        self.assertEqual(response.status_code, 200)

    def test_login_get_muestra_formulario(self):
        """GET /login/ devuelve el formulario correctamente."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'usuarios/login.html')

    # ── Logout ───────────────────────────────────────────────────

    def test_logout_redirige_landing(self):
        """Logout de un usuario autenticado redirige a la raíz."""
        self.client.login(email='usuario@test.com', password='pass1234!')
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)

    # ── Registro ─────────────────────────────────────────────────

    def test_registro_exitoso_crea_usuario(self):
        """Registro con datos válidos crea el usuario en la BD."""
        response = self.client.post(reverse('register'), {
            'username': 'nuevousuario',
            'email': 'nuevo@test.com',
            'password1': 'Segura123!',
            'password2': 'Segura123!',
        })
        # Redirige tras registro exitoso
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Usuario.objects.filter(email='nuevo@test.com').exists())

    def test_registro_email_duplicado(self):
        """Registro con email ya existente rechaza la solicitud."""
        response = self.client.post(reverse('register'), {
            'username': 'otro',
            'email': 'usuario@test.com',  # ya existe
            'password1': 'Segura123!',
            'password2': 'Segura123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Usuario.objects.filter(email='usuario@test.com').count(), 1)

    def test_registro_passwords_no_coinciden(self):
        """Registro con contraseñas distintas rechaza la solicitud."""
        response = self.client.post(reverse('register'), {
            'username': 'otro2',
            'email': 'otro2@test.com',
            'password1': 'Segura123!',
            'password2': 'Diferente456!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Usuario.objects.filter(email='otro2@test.com').exists())

    # ── Acceso no autenticado ─────────────────────────────────────

    def test_perfil_sin_sesion_redirige_login(self):
        """Acceder a /perfil/ sin sesión activa redirige a login."""
        response = self.client.get(reverse('perfil'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])


class PerfilTestCase(TestCase):
    """Pruebas de edición del perfil y cambio de contraseña."""

    def setUp(self):
        self.client = Client()
        self.user = Usuario.objects.create_user(
            email='perfil@test.com',
            password='pass1234!',
            username='perfiluser'
        )
        self.client.login(email='perfil@test.com', password='pass1234!')

    def test_perfil_get_retorna_200(self):
        """GET /perfil/ devuelve la vista con código 200."""
        response = self.client.get(reverse('perfil'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'usuarios/perfil.html')

    def test_perfil_tab_notificaciones(self):
        """GET /perfil/?tab=notificaciones carga la pestaña correcta."""
        response = self.client.get(reverse('perfil') + '?tab=notificaciones')
        self.assertEqual(response.status_code, 200)

    def test_cambio_password_exitoso(self):
        """Cambio de contraseña con datos correctos retorna ok=True."""
        # El campo que activa esta rama en perfil_view es 'cambiar_password'
        # Los campos del PasswordChangeForm de Django son: old_password, new_password1, new_password2
        response = self.client.post(
            reverse('perfil'),
            {
                'cambiar_password': '1',
                'old_password': 'pass1234!',
                'new_password1': 'NuevaPass789!',
                'new_password2': 'NuevaPass789!',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('ok'))

    def test_cambio_password_actual_incorrecto(self):
        """Cambio de contraseña con contraseña actual incorrecta retorna ok=False."""
        response = self.client.post(
            reverse('perfil'),
            {
                'cambiar_password': '1',
                'old_password': 'wrongpass',
                'new_password1': 'NuevaPass789!',
                'new_password2': 'NuevaPass789!',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data.get('ok'))


class ModeloUsuarioTestCase(TestCase):
    """Pruebas del modelo Usuario."""

    def test_crear_usuario_con_email(self):
        """El usuario se crea correctamente con email como identificador."""
        user = Usuario.objects.create_user(
            email='modelo@test.com',
            password='pass1234!',
            username='modelouser'
        )
        self.assertEqual(str(user), 'modelo@test.com')

    def test_nombre_usuario_fallback_email(self):
        """nombre_usuario devuelve la parte local del email si no hay username."""
        user = Usuario.objects.create_user(
            email='sinusername@test.com',
            password='pass1234!',
            username=''
        )
        self.assertEqual(user.nombre_usuario, 'sinusername')

    def test_preferencias_creadas_con_usuario(self):
        """Al crear un usuario, sus preferencias se crean automáticamente via signal."""
        user = Usuario.objects.create_user(
            email='prefs@test.com',
            password='pass1234!',
            username='prefsuser'
        )
        # El signal post_save del model Usuario las crea automáticamente
        self.assertTrue(Preferencias.objects.filter(usuario=user).exists())
