from rest_framework import serializers
from .models import Presupuesto
from datetime import date
from django.db.models import Sum
from decimal import Decimal
from movimientos.models import Movimiento

class PresupuestoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    class Meta:
        model = Presupuesto
        fields = '__all__'
        read_only_fields = ('fecha_creacion', 'usuario')
    
    def create(self, validated_data):
        validated_data['usuario'] = self.context['request'].user
        return super().create(validated_data)

    def validate_limite(self, value):
        if value <= 0:
            raise serializers.ValidationError("El límite debe ser mayor a 0")
        return value

    def validate_fecha_inicio(self, value):
        if value < date.today():
            raise serializers.ValidationError("La fecha inicio no puede ser en el pasado")
        return value

    def validate(self, data):
        usuario = self.context['request'].user

        categoria = data.get('categoria') or self.instance.categoria
        isActivo = data.get('isActivo')

        # Solo validar si se está activando
        if isActivo is True:
            queryset = Presupuesto.objects.filter(
                usuario=usuario,
                categoria=categoria,
                isActivo=True
            )

            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)

            if queryset.exists():
                raise serializers.ValidationError(
                    "Ya existe un presupuesto activo para esta categoría"
                )

        fecha_inicio = data.get('fecha_inicio') or self.instance.fecha_inicio
        fecha_fin = data.get('fecha_fin') or self.instance.fecha_fin

        if fecha_inicio and fecha_fin:
            if fecha_fin <= fecha_inicio:
                raise serializers.ValidationError(
                    "La fecha fin debe ser mayor a la fecha inicio"
                )

        return data