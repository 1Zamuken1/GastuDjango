from django.contrib.auth.forms import UserCreationForm
from .models import Usuario


class UsuarioCreationForm(UserCreationForm):
    """
    Formulario de registro que extiende UserCreationForm
    usando el modelo personalizado Usuario.
    """

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('username', 'email', 'telefono')