import re
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import Usuario


# ──────────────────────────────────────────────────────────────
#  REGISTRO
# ──────────────────────────────────────────────────────────────

class UsuarioCreationForm(UserCreationForm):
    """
    Formulario de registro con validaciones personalizadas.
    Extiende UserCreationForm usando el modelo personalizado Usuario.
    El nombre de usuario (username) es libre y puede repetirse.
    El correo electronico es unico y es el identificador de la cuenta.
    """

    email = forms.EmailField(
        required=True,
        label='Correo electronico',
        error_messages={
            'required': 'El correo electronico es obligatorio.',
            'invalid': 'Ingresa un correo electronico valido.',
        }
    )

    username = forms.CharField(
        required=True,
        label='Nombre de usuario',
        help_text='Como quieres que te veamos. Puede repetirse entre usuarios.',
        error_messages={
            'required': 'El nombre de usuario es obligatorio.',
        }
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('username', 'email', 'telefono')

    # ── Username — solo longitud y caracteres, sin unicidad ─────
    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()

        if len(username) < 3:
            raise ValidationError('El nombre de usuario debe tener al menos 3 caracteres.')

        if len(username) > 150:
            raise ValidationError('El nombre de usuario no puede superar los 150 caracteres.')

        if not re.match(r'^[a-zA-Z0-9_ .\-]+$', username):
            raise ValidationError(
                'Solo se permiten letras, numeros, espacios, guiones bajos (_), '
                'puntos (.) y guiones (-).'
            )

        return username

    # ── Email — unico en el sistema ─────────────────────────────
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()

        if not email:
            raise ValidationError('El correo electronico es obligatorio.')

        if Usuario.objects.filter(email__iexact=email).exists():
            raise ValidationError('Ya existe una cuenta con este correo electronico.')

        return email

    # ── Telefono ─────────────────────────────────────────────────
    def clean_telefono(self):
        telefono = (self.cleaned_data.get('telefono') or '').strip()

        if not telefono:
            return telefono  # campo opcional

        digits = re.sub(r'[\s\-\+]', '', telefono)
        if not digits.isdigit():
            raise ValidationError('El telefono solo puede contener numeros, espacios, + y -.')

        if len(digits) < 7 or len(digits) > 15:
            raise ValidationError('El telefono debe tener entre 7 y 15 digitos.')

        return telefono

    # ── Contrasena ───────────────────────────────────────────────
    def clean_password1(self):
        password = self.cleaned_data.get('password1', '')

        if len(password) < 8:
            raise ValidationError('La contrasena debe tener al menos 8 caracteres.')

        if not re.search(r'[A-Z]', password):
            raise ValidationError('La contrasena debe incluir al menos una letra mayuscula.')

        if not re.search(r'\d', password):
            raise ValidationError('La contrasena debe incluir al menos un numero.')

        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
            raise ValidationError('La contrasena debe incluir al menos un caracter especial (!@#$%...).')

        return password

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError('Las contrasenas no coinciden.')

        return password2


# ──────────────────────────────────────────────────────────────
#  LOGIN  (por email + contrasena)
# ──────────────────────────────────────────────────────────────

class LoginForm(forms.Form):
    """
    Formulario de login personalizado que autentica con EMAIL + contrasena.
    No extiende AuthenticationForm porque ese usa username como campo fijo.
    """

    email = forms.EmailField(
        label='Correo electronico',
        max_length=254,
        error_messages={
            'required': 'El correo electronico es obligatorio.',
            'invalid': 'Ingresa un correo electronico valido.',
        }
    )

    password = forms.CharField(
        label='Contrasena',
        widget=forms.PasswordInput,
        error_messages={
            'required': 'La contrasena es obligatoria.',
        }
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self._usuario_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        password = self.cleaned_data.get('password', '')

        if email and password:
            self._usuario_cache = authenticate(
                self.request,
                email=email,
                password=password,
            )
            if self._usuario_cache is None:
                raise ValidationError(
                    'Correo o contrasena incorrectos. Verifica tus datos e intenta de nuevo.'
                )
            if not self._usuario_cache.is_active:
                raise ValidationError('Esta cuenta esta desactivada. Contacta al administrador.')

        return self.cleaned_data

    def get_user(self):
        """Devuelve el usuario autenticado tras validar el formulario."""
        return self._usuario_cache