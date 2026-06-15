import re
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.urls import reverse
from .models import Usuario, Preferencias


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

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()

        if not email:
            raise ValidationError('El correo electronico es obligatorio.')

        if Usuario.objects.filter(email__iexact=email).exists():
            raise ValidationError('Ya existe una cuenta con este correo electronico.')

        return email

    def clean_telefono(self):
        telefono = (self.cleaned_data.get('telefono') or '').strip()

        if not telefono:
            return telefono

        digits = re.sub(r'[\s\-\+]', '', telefono)
        if not digits.isdigit():
            raise ValidationError('El telefono solo puede contener numeros, espacios, + y -.')

        if len(digits) < 7 or len(digits) > 15:
            raise ValidationError('El telefono debe tener entre 7 y 15 digitos.')

        return telefono

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
                # Comprobar si existe el usuario pero no tiene contraseña (creado con Google)
                try:
                    user_obj = Usuario.objects.get(email__iexact=email)
                    if not user_obj.has_usable_password():
                        reset_url = reverse('account_reset_password')
                        raise ValidationError(
                            mark_safe(
                                'Parece que usaste Google para crear esta cuenta.<br>'
                                '<div class="mt-2 flex items-center gap-2">'
                                '<a href="/auth/google/login/" class="bg-emerald-500 hover:bg-emerald-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium transition-colors">Iniciar con Google</a>'
                                '<span class="text-xs text-slate-400">o</span>'
                                f'<a href="{reset_url}" class="text-xs text-emerald-600 hover:text-emerald-500 font-medium underline">Crear contraseña</a>'
                                '</div>'
                            )
                        )
                except Usuario.DoesNotExist:
                    pass

                raise ValidationError(
                    'Correo o contrasena incorrectos. Verifica tus datos e intenta de nuevo.'
                )
            if not self._usuario_cache.is_active:
                raise ValidationError('Esta cuenta esta desactivada. Contacta al administrador.')

        return self.cleaned_data

    def get_user(self):
        """Devuelve el usuario autenticado tras validar el formulario."""
        return self._usuario_cache


# ──────────────────────────────────────────────────────────────
#  PERFIL — datos personales (username + telefono)
# ──────────────────────────────────────────────────────────────

class PerfilForm(forms.ModelForm):
    """
    Formulario simple para editar datos basicos del perfil.
    """

    class Meta:
        model = Usuario
        fields = ('username', 'telefono')
        labels = {
            'username': 'Nombre de usuario',
            'telefono': 'Telefono',
        }

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

    def clean_telefono(self):
        telefono = (self.cleaned_data.get('telefono') or '').strip()

        if not telefono:
            return ''

        digits = re.sub(r'[\s\-\+]', '', telefono)
        if not digits.isdigit():
            raise ValidationError('El telefono solo puede contener numeros, + y -.')

        if len(digits) < 7 or len(digits) > 15:
            raise ValidationError('El telefono debe tener entre 7 y 15 digitos.')

        return telefono


# ──────────────────────────────────────────────────────────────
#  PREFERENCIAS DE NOTIFICACIONES (editable)
# ──────────────────────────────────────────────────────────────

class PreferenciasForm(forms.ModelForm):
    """
    Formulario para configurar alertas de notificacion.
    El modelo Preferencias tiene campos genericos, pero aqui los exponemos
    como toggles individuales para cada tipo de alerta.
    """

    umbral_advertencia_porcentaje = forms.IntegerField(
        min_value=20, max_value=100,
        label='Umbral de gastos (%)',
        help_text='Alerta al superar este porcentaje de tus ingresos',
        widget=forms.NumberInput(attrs={
            'min': '20', 'max': '100', 'step': '5',
        }),
    )

    egreso_grande_porcentaje = forms.IntegerField(
        min_value=5, max_value=80,
        label='Egreso grande (%)',
        help_text='Alerta si un solo gasto supera este porcentaje de ingresos',
        widget=forms.NumberInput(attrs={
            'min': '5', 'max': '80', 'step': '5',
        }),
    )

    alerta_egreso_grande = forms.BooleanField(
        required=False, label='Egreso grande',
        help_text='Cuando un solo gasto es muy grande respecto a tus ingresos',
    )
    alerta_deficit = forms.BooleanField(
        required=False, label='Balance en deficit',
        help_text='Cuando tus egresos superan tus ingresos',
    )
    alerta_patron_inusual = forms.BooleanField(
        required=False, label='Patron inusual',
        help_text='Cuando detecta comportamiento de gasto extrano',
    )
    alerta_presupuesto = forms.BooleanField(
        required=False, label='Umbral mensual',
        help_text='Cuando llevas un alto porcentaje gastado del mes',
    )
    alerta_aporte_proximo = forms.BooleanField(
        required=False, label='Aproximacion de pago',
        help_text='Recordatorios de pagos proximos',
    )
    alerta_proyeccion = forms.BooleanField(
        required=False, label='Proyeccion de sobregasto',
        help_text='Cuando la proyeccion indica que gastarás mas de lo ganado',
    )
    alerta_velocidad = forms.BooleanField(
        required=False, label='Velocidad de gasto',
        help_text='Cuando gastas muy rapido en los primeros dias del mes',
    )
    alerta_gastos_hormiga = forms.BooleanField(
        required=False, label='Gastos hormiga',
        help_text='Cuando acumulas muchos pequenos gastos que suman mucho',
    )

    alerta_dia_critico = forms.BooleanField(
        required=False, label='Dia critico',
        help_text='Cuando llevas mucho gastado respecto al dia del mes',
    )

    class Meta:
        model = Preferencias
        fields = (
            'umbral_advertencia_porcentaje',
            'egreso_grande_porcentaje',
            'alerta_egreso_grande',
            'alerta_deficit',
            'alerta_patron_inusual',
            'alerta_presupuesto',
            'alerta_aporte_proximo',
            'alerta_aporte_dias_anticipacion',
        )
        labels = {
            'alerta_aporte_dias_anticipacion': 'Dias de anticipacion',
        }
        widgets = {
            'umbral_advertencia_porcentaje': forms.NumberInput(attrs={
                'class': 'perfil-input',
            }),
            'egreso_grande_porcentaje': forms.NumberInput(attrs={
                'class': 'perfil-input',
            }),
            'alerta_aporte_dias_anticipacion': forms.NumberInput(attrs={
                'min': '1', 'max': '14', 'step': '1',
                'class': 'perfil-input',
            }),
        }
