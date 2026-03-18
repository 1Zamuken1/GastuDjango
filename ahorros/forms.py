from django import forms
from .models import AhorroMeta, AporteAhorro
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

    # --- VALIDACIONES PERSONALIZADAS ---

    def clean_monto_meta(self):
        monto = self.cleaned_data.get('monto_meta')
        if monto  is None or monto <= 0:
            raise forms.ValidationError("El monto meta debe ser mayor a 0.")
        return monto

    def clean_cantidad_cuotas(self):
        cuotas = self.cleaned_data.get('cantidad_cuotas')
        if cuotas  is None or cuotas <= 0:
            raise forms.ValidationError("La cantidad de cuotas debe ser mayor a 0.")
        return cuotas

    def clean_fecha_meta(self):
        fecha = self.cleaned_data.get('fecha_meta')
        hoy = timezone.now().date()
        if fecha <= hoy:
            raise forms.ValidationError("La fecha meta debe ser posterior a la fecha actual.")
        return fecha


class AporteAhorroForm(forms.ModelForm):
    
    class Meta:
        model = AporteAhorro
        fields = ['aporte']

    def clean_aporte(self):
        monto_aporte = self.cleaned_data.get('aporte')
        if monto_aporte is None or monto_aporte <= 0:
            raise forms.ValidationError("El aporte debe ser mayor a 0.")
        return monto_aporte