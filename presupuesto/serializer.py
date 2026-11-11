from django.utils import timezone
from rest_framework import serializers

from .models import Presupuesto


class PresupuestoSerializer(serializers.ModelSerializer):
    """Serializer de Presupuesto. Expone el nombre de la categoría como solo lectura."""
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    categoria_icono = serializers.CharField(source='categoria.icono', read_only=True)

    class Meta:
        model = Presupuesto
        fields = '__all__'
        read_only_fields = ('fecha_creacion', 'usuario')

    def create(self, validated_data):
        validated_data['usuario'] = self.context['request'].user
        return super().create(validated_data)

    def validate_limite(self, value):
        if value <= 0:
            raise serializers.ValidationError("El límite debe ser mayor a 0.")
        return value

    def validate_categoria(self, value):
        if value.tipo != 'EGRESO':
            raise serializers.ValidationError("Los presupuestos solo aplican a categorías de egreso.")
        return value

    def validate_fecha_fin(self, value):
        """La fecha fin no puede quedar en el pasado.

        Al editar solo se valida si la fecha cambia, para poder ajustar el
        límite de un presupuesto que termina hoy o que ya cerró.
        """
        if self.instance and value == self.instance.fecha_fin:
            return value
        if value < timezone.localdate():
            raise serializers.ValidationError("La fecha final no puede ser anterior a hoy.")
        return value

    def validate(self, data):
        usuario = self.context['request'].user
        categoria = data.get('categoria') or (self.instance.categoria if self.instance else None)
        is_activo = data.get('is_activo', self.instance.is_activo if self.instance else None)
        fecha_inicio = data.get('fecha_inicio') or (self.instance.fecha_inicio if self.instance else None)
        fecha_fin = data.get('fecha_fin') or (self.instance.fecha_fin if self.instance else None)

        if is_activo is True:
            queryset = Presupuesto.objects.filter(
                usuario=usuario, categoria=categoria, is_activo=True
            )
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            if queryset.exists():
                raise serializers.ValidationError(
                    "Ya existe un presupuesto activo para esta categoría."
                )
            if fecha_fin and fecha_fin < timezone.localdate():
                raise serializers.ValidationError(
                    "Este presupuesto ya terminó. Usa Renovar para crear el del siguiente período."
                )

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise serializers.ValidationError(
                "La fecha de fin debe ser posterior a la fecha de inicio."
            )

        return data
