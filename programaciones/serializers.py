from django.utils import timezone
from rest_framework import serializers

from .models import Programacion
from .services import monto_mensual_estimado, proxima_inicial, recalcular_tras_edicion


class ProgramacionSerializer(serializers.ModelSerializer):
    """Serializer de Programacion. Expone nombre y tipo de la categoría como solo lectura.

    El campo ``tipo`` del modelo se sincroniza siempre con la categoría,
    tanto al crear como al editar.
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    tipo = serializers.CharField(source='categoria.tipo', read_only=True)
    frecuencia_label = serializers.CharField(source='get_frecuencia_display', read_only=True)
    monto_mensual = serializers.SerializerMethodField()

    class Meta:
        model = Programacion
        fields = '__all__'
        read_only_fields = ('fecha_creacion', 'usuario', 'tipo', 'proxima_ejecucion')

    def get_monto_mensual(self, obj):
        """Equivalente mensual aproximado del monto según la frecuencia."""
        return float(monto_mensual_estimado(obj.monto_programado, obj.frecuencia))

    def create(self, validated_data):
        validated_data['usuario'] = self.context['request'].user
        validated_data['tipo'] = validated_data['categoria'].tipo
        validated_data['proxima_ejecucion'] = proxima_inicial(
            validated_data['fecha_inicio'], validated_data['frecuencia'], timezone.localdate()
        )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Sincroniza el tipo y recalcula la próxima ejecución si cambia el calendario."""
        if 'categoria' in validated_data:
            validated_data['tipo'] = validated_data['categoria'].tipo

        cambio_calendario = (
            ('fecha_inicio' in validated_data and validated_data['fecha_inicio'] != instance.fecha_inicio)
            or ('frecuencia' in validated_data and validated_data['frecuencia'] != instance.frecuencia)
        )
        reactivada = validated_data.get('activo') is True and not instance.activo
        hoy = timezone.localdate()
        hoy_ya_resuelto = bool(
            instance.fecha_inicio <= hoy
            and instance.proxima_ejecucion
            and instance.proxima_ejecucion > hoy
        )

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        recalcular_tras_edicion(instance, cambio_calendario, reactivada, hoy, hoy_ya_resuelto)
        instance.save()
        return instance

    def validate_monto_programado(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor a 0.")
        return value

    def validate(self, data):
        fecha_inicio = data.get('fecha_inicio', getattr(self.instance, 'fecha_inicio', None))
        fecha_fin = data.get('fecha_fin', getattr(self.instance, 'fecha_fin', None))
        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise serializers.ValidationError(
                "La fecha fin debe ser posterior a la fecha de inicio."
            )
        if data.get('activo') is True and self.instance and not self.instance.activo:
            if fecha_fin and fecha_fin < timezone.localdate():
                raise serializers.ValidationError(
                    "Esta programación ya terminó. Cambia la fecha fin para reactivarla."
                )
        return data
