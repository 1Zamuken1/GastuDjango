from django import forms
from .models import Categoria


class CategoriaForm(forms.ModelForm):
    """
    Formulario para crear y editar categorías.
    Solo accesible por Admin.
    """

    class Meta:
        model = Categoria
        fields = ['nombre', 'tipo', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Salario'
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-control'
            }),
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción opcional',
                'maxlength': '255'
            })
        }