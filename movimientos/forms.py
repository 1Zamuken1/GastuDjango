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

    def __init__(self, tipo=None, usuario=None, *args, **kwargs):
        """
        Filtra categorías según tipo y guarda el usuario para validaciones.

        Args:
            tipo (str): 'INGRESO' o 'EGRESO'.
            usuario: instancia del usuario autenticado.
        """
        super().__init__(*args, **kwargs)
        self.usuario = usuario
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

    def clean(self):
        """
        Valida que un egreso no supere la ganancia acumulada del usuario.

        Raises:
            ValidationError: si el egreso supera el saldo disponible.
        """
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        monto = cleaned_data.get('monto')

        if tipo == 'EGRESO' and monto and self.usuario:
            from dashboard.models import ResumenMensual
            from django.db.models import Sum
            from decimal import Decimal

            # Obtener ganancia acumulada del resumen más reciente
            ultimo_resumen = ResumenMensual.objects.filter(
                usuario=self.usuario
            ).order_by('-anio', '-mes').first()

            ganancia_acumulada = ultimo_resumen.ganancia_acumulada if ultimo_resumen else Decimal('0')

            # Si es edición, devolver el monto anterior al disponible
            monto_anterior = Decimal('0')
            if self.instance and self.instance.pk:
                monto_anterior = self.instance.monto

            saldo_disponible = ganancia_acumulada + monto_anterior

            if monto > saldo_disponible:
                raise forms.ValidationError(
                    f'No tienes saldo suficiente. '
                    f'Tu ganancia acumulada es de ${ganancia_acumulada:,.2f} '
                    f'y estás intentando gastar ${monto:,.2f}.'
                )

        return cleaned_data