from django import forms
from .models import Movimiento, Categoria


class MovimientoForm(forms.ModelForm):
    """
    Formulario para crear y editar movimientos financieros.
    El tipo y la categoría inicial vienen por contexto desde la vista,
    pero el usuario puede cambiar la categoría en caso de error.
    """

    class Meta:
        model = Movimiento
        fields = ['monto', 'descripcion', 'categoria', 'tipo']
        widgets = {
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 150000',
                'min': '0.01',
                'step': '0.01'
            }),
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción opcional (máx. 255 caracteres)',
                'maxlength': '255'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-control'
            }),
            'tipo': forms.HiddenInput()
        }

    def __init__(self, tipo=None, *args, **kwargs):
        """
        Filtra las categorías disponibles según el tipo de movimiento.

        Args:
            tipo (str): 'INGRESO' o 'EGRESO' — viene del contexto de la vista.
        """
        super().__init__(*args, **kwargs)
        if tipo:
            self.fields['categoria'].queryset = Categoria.objects.filter(
                tipo=tipo,
                activo=True
            )
            self.initial['tipo'] = tipo

    def clean_monto(self):
        """
        Valida que el monto sea positivo.

        Returns:
            Decimal: monto validado.

        Raises:
            ValidationError: si el monto es 0 o negativo.
        """
        monto = self.cleaned_data.get('monto')
        if monto is not None and monto <= 0:
            raise forms.ValidationError('El monto debe ser mayor a cero.')
        return monto