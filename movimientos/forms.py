from django import forms

from categorias.models import Categoria
from .models import Movimiento


class MovimientoForm(forms.ModelForm):
    """
    Formulario de creación y edición de movimientos.

    Acepta dos kwargs adicionales:
    - tipo_movimiento: filtra el queryset de categorías al tipo correcto
      (INGRESO o EGRESO) según la vista desde la que se use.
    - disponible: Decimal con el saldo disponible del usuario en el mes actual.
      Solo se usa cuando tipo_movimiento es EGRESO para impedir que el monto
      supere el dinero disponible.

    fecha_registro NO se expone al usuario: el modelo usa auto_now_add=True,
    por lo que se llena automáticamente con la fecha y hora del servidor al guardar.
    """

    class Meta:
        model = Movimiento
        fields = ['tipo', 'categoria', 'descripcion', 'monto']
        widgets = {
            'tipo': forms.HiddenInput(),
            'descripcion': forms.TextInput(attrs={'placeholder': 'Descripción del movimiento'}),
            'monto': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0.01'}),
        }
        labels = {
            'monto': 'Monto',
            'descripcion': 'Descripción',
            'categoria': 'Categoría',
        }
        error_messages = {
            'categoria': {
                'required': 'La categoría es obligatoria.',
                'invalid_choice': 'La categoría seleccionada no es válida.',
            },
            'monto': {
                'required': 'El monto es obligatorio.',
                'invalid': 'El monto debe ser un número válido.',
            }
        }

    def __init__(self, *args, tipo_movimiento=None, disponible=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._disponible = disponible
        qs = Categoria.objects.filter(activo=True, es_sistema=False)
        if tipo_movimiento in ('INGRESO', 'EGRESO'):
            qs = qs.filter(tipo=tipo_movimiento)
        self.fields['categoria'].queryset = qs.order_by('nombre')
        self.fields['categoria'].empty_label = 'Seleccionar categoría'

    def clean_tipo(self):
        """Validar que el tipo sea uno de los valores permitidos."""
        tipo = self.cleaned_data.get('tipo')
        if tipo not in ('INGRESO', 'EGRESO'):
            raise forms.ValidationError('Tipo de movimiento no válido.')
        return tipo

    def clean_monto(self):
        """
        Valida que el monto sea mayor a cero.
        Para egresos, también valida que no supere el disponible del mes actual.
        """
        monto = self.cleaned_data.get('monto')
        if monto is not None and monto <= 0:
            raise forms.ValidationError('El monto debe ser mayor que cero.')

        tipo = self.cleaned_data.get('tipo')
        if (
            tipo == 'EGRESO'
            and monto is not None
            and self._disponible is not None
            and monto > self._disponible
        ):
            raise forms.ValidationError(
                f'El monto excede tu saldo disponible (${self._disponible:,.0f}). '
                f'Registra un ingreso primero o reduce el monto del egreso.'
            )

        return monto 