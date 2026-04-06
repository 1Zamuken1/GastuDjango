from rest_framework import serializers
from .models import Programacion


class ProgramacionSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    tipo             = serializers.CharField(source='categoria.tipo', read_only=True)

    class Meta:
        model  = Programacion
        fields = '__all__'
        read_only_fields = ('fecha_creacion', 'usuario', 'tipo')

    def create(self, validated_data):
        validated_data['usuario'] = self.context['request'].user
        validated_data['tipo']    = validated_data['categoria'].tipo
        return super().create(validated_data)

    def validate_monto_programado(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor a 0")
        return value
    def validate(self, data):
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin    = data.get('fecha_fin')

        if fecha_inicio and fecha_fin:
            if fecha_fin <= fecha_inicio:
                raise serializers.ValidationError(
                    "La fecha fin debe ser mayor a la fecha inicio"
                )
        return data