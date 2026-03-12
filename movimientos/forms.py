from django import forms

from categorias.models import Categoria
from .models import Movimiento


class MovimientoForm(forms.ModelForm):
    """
    Formulario de creación y edición de movimientos.

    El campo 'tipo' se pasa como campo oculto desde el template —
    la vista nunca debe confiar ciegamente en él; el clean lo valida.

    fecha_registro se declara fuera de Meta.fields porque el modelo
    lo tiene como non-editable. Al declararlo como atributo de clase
    Django lo incluye en el form sin pasar por la validación del modelo.
    """

    fecha_registro = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Fecha',
    )

    class Meta:
        model = Movimiento
        fields = ['tipo', 'monto', 'descripcion', 'categoria']
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].queryset = Categoria.objects.filter(activo=True).order_by('nombre')
        self.fields['categoria'].empty_label = 'Seleccionar categoría'

    def clean_tipo(self):
        """Validar que el tipo sea uno de los valores permitidos."""
        tipo = self.cleaned_data.get('tipo')
        if tipo not in ('INGRESO', 'EGRESO'):
            raise forms.ValidationError('Tipo de movimiento no válido.')
        return tipo

    def clean_monto(self):
        """Validar que el monto sea mayor a cero."""
        monto = self.cleaned_data.get('monto')
        if monto is not None and monto <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return monto