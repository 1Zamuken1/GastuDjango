from django import forms
from .models import AhorroMeta, AporteAhorro
from categorias.models import Categoria
from django.utils import timezone

class AhorroMetaForm(forms.ModelForm):
    
    class Meta:
        model = AhorroMeta
        # Solo incluimos lo que el usuario llena
        fields = [
            'categoria', 
            'monto_meta', 
            'frecuencia', 
            'fecha_meta', 
            'cantidad_cuotas',
            'descripcion',
        ]
        # Añadimos widgets para que se vea bien (calendario en la fecha)
        widgets = {
            'monto_meta': forms.NumberInput(attrs={'min': '0.01'}),
            'fecha_meta': forms.DateInput(attrs={'type': 'date'}),
            'cantidad_cuotas': forms.NumberInput(attrs={'min': '1'}),
            'descripcion': forms.Textarea(attrs={'rows': 2, 'placeholder': '¿Para qué es este ahorro?'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # SOLO categorías de tipo AHORRO
        qs = Categoria.objects.filter(tipo=Categoria.TipoCategoria.AHORRO, activo=True)
        
        if self.instance and self.instance.pk and self.instance.categoria_id:
            qs = qs | Categoria.objects.filter(pk=self.instance.categoria_id)
            
        self.fields['categoria'].queryset = qs.order_by('nombre')
        # Quitamos la obligatoriedad automática de estos campos
        self.fields['fecha_meta'].required = False
        self.fields['cantidad_cuotas'].required = False
    # --- VALIDACIONES PERSONALIZADAS ---

    def clean_monto_meta(self):
        monto = self.cleaned_data.get('monto_meta')
        if monto  is None or monto <= 0:
            raise forms.ValidationError("El monto meta debe ser mayor a 0.")
        return monto

    def clean(self): #valida fecha meta y cantidad de cuotas
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha_meta')
        cuotas = cleaned_data.get('cantidad_cuotas')
        hoy = timezone.now().date()

        if not fecha and not cuotas:
            raise forms.ValidationError(
                "Debes ingresar fecha meta o cantidad de cuotas."
            )
            
        if fecha and cuotas:
            raise forms.ValidationError(
                "Debes ingresar SOLO fecha meta o cantidad de cuotas, no ambos."
            )
            
        if fecha and fecha < hoy:
            raise forms.ValidationError(
                "La fecha meta no puede estar en el pasado."
            )

        return cleaned_data

class AporteAhorroForm(forms.ModelForm):
    
    class Meta:
        model = AporteAhorro
        fields = ['aporte']

    def clean_aporte(self):
        monto_aporte = self.cleaned_data.get('aporte')
        if monto_aporte is None or monto_aporte <= 0:
            raise forms.ValidationError("El aporte debe ser mayor a 0.")
        return monto_aporte