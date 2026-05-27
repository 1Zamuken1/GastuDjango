"""
Adaptador personalizado de django-allauth para GastuApp.
Ruta: usuarios/adapters.py

Resuelve la incompatibilidad entre el modelo Usuario (AbstractUser con username
requerido a nivel de BD) y el flujo de registro via Google OAuth, donde allauth
no pide username al usuario. El adaptador genera uno automaticamente a partir
del email, garantizando unicidad.
"""

import uuid
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Adaptador de cuentas sociales para GastuApp.

    Extiende el comportamiento por defecto de allauth para generar
    automaticamente un username unico cuando un usuario se registra
    via Google OAuth, dado que el modelo Usuario hereda de AbstractUser
    y el campo username es requerido a nivel de base de datos.
    """

    def populate_user(self, request, sociallogin, data):
        """
        Rellena los campos del usuario a partir de los datos de Google.

        Si allauth no asigna un username (porque ACCOUNT_USERNAME_REQUIRED
        es False y el campo no esta en ACCOUNT_SIGNUP_FIELDS), se genera
        uno automaticamente desde la parte local del email. Se añade un
        sufijo aleatorio de 6 caracteres para garantizar unicidad en caso
        de colisiones.

        Parametros
        ----------
        request : HttpRequest
        sociallogin : SocialLogin
        data : dict
            Datos del perfil retornados por Google (email, name, etc.)

        Retorna
        -------
        Usuario
            Instancia del modelo con username garantizado.
        """
        user = super().populate_user(request, sociallogin, data)

        if not getattr(user, 'username', None):
            email = data.get('email') or ''
            base_username = email.split('@')[0] if email else 'usuario'
            # Sufijo de 6 caracteres para evitar colisiones
            suffix = uuid.uuid4().hex[:6]
            user.username = f'{base_username}_{suffix}'

        return user