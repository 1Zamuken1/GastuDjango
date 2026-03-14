import re
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import Usuario


# ──────────────────────────────────────────────────────────────
#  REGISTRO
# ──────────────────────────────────────────────────────────────

class UsuarioCreationForm(UserCreationForm):
    """
    Formulario de registro con validaciones personalizadas.
    Extiende UserCreationForm usando el modelo personalizado Usuario.
    """

    email = forms.EmailField(
        required=True,
        error_messages={
            'required': 'El correo electrónico es obligatorio.',
            'invalid': 'Ingresa un correo electrónico válido.',
        }
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('username', 'email', 'telefono')

    # ── Username ────────────────────────────────────────────────
    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()

        if len(username) < 3:
            raise ValidationError('El nombre de usuario debe tener al menos 3 caracteres.')

        if len(username) > 30:
            raise ValidationError('El nombre de usuario no puede superar los 30 caracteres.')

        if not re.match(r'^[a-zA-Z0-9_ .\-]+$', username):
            raise ValidationError(
                'Solo se permiten letras, números, espacios, guiones bajos (_), '
                'puntos (.) y guiones (-).'
            )

        if Usuario.objects.filter(username__iexact=username).exists():
            raise ValidationError('Este nombre de usuario ya está en uso.')

        return username

    # ── Email ───────────────────────────────────────────────────
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()

        if not email:
            raise ValidationError('El correo electrónico es obligatorio.')

        if Usuario.objects.filter(email__iexact=email).exists():
            raise ValidationError('Ya existe una cuenta con este correo electrónico.')

        return email

    # ── Teléfono ────────────────────────────────────────────────
    def clean_telefono(self):
        telefono = (self.cleaned_data.get('telefono') or '').strip()

        if not telefono:
            return telefono  # campo opcional

        digits = re.sub(r'[\s\-\+]', '', telefono)
        if not digits.isdigit():
            raise ValidationError('El teléfono solo puede contener números, espacios, + y -.')

        if len(digits) < 7 or len(digits) > 15:
            raise ValidationError('El teléfono debe tener entre 7 y 15 dígitos.')

        return telefono

    # ── Contraseña ──────────────────────────────────────────────
    def clean_password1(self):
        password = self.cleaned_data.get('password1', '')

        if len(password) < 8:
            raise ValidationError('La contraseña debe tener al menos 8 caracteres.')

        if not re.search(r'[A-Z]', password):
            raise ValidationError('La contraseña debe incluir al menos una letra mayúscula.')

        if not re.search(r'\d', password):
            raise ValidationError('La contraseña debe incluir al menos un número.')

        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
            raise ValidationError('La contraseña debe incluir al menos un carácter especial (!@#$%...).')

        return password

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise ValidationError('Las contraseñas no coinciden.')

        return password2


# ──────────────────────────────────────────────────────────────
#  LOGIN
# ──────────────────────────────────────────────────────────────

class LoginForm(AuthenticationForm):
    """
    Formulario de login con validaciones y mensajes en español.
    Extiende AuthenticationForm de Django.
    """

    username = forms.CharField(
        label='Usuario',
        max_length=150,
        error_messages={
            'required': 'El nombre de usuario es obligatorio.',
        }
    )

    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput,
        error_messages={
            'required': 'La contraseña es obligatoria.',
        }
    )

    error_messages = {
        'invalid_login': (
            'Usuario o contraseña incorrectos. '
            'Verifica tus datos e intenta de nuevo.'
        ),
        'inactive': 'Esta cuenta está desactivada. Contacta al administrador.',
    }

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()

        if not username:
            raise ValidationError('El nombre de usuario es obligatorio.')

        if len(username) > 150:
            raise ValidationError('El nombre de usuario es demasiado largo.')

        return username

    def clean_password(self):
        password = self.cleaned_data.get('password', '')

        if not password:
            raise ValidationError('La contraseña es obligatoria.')

        return password