
from rest_framework import viewsets, permissions
from .models import Categoria
from rest_framework import serializers

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'


class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Categoria.objects.filter(activo=True)
    serializer_class = CategoriaSerializer
    permission_classes = [permissions.IsAuthenticated]