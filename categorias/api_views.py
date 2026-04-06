
from rest_framework import viewsets, permissions
from .models import Categoria
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import serializers

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'


class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Categoria.objects.filter(activo=True)
    serializer_class = CategoriaSerializer
    permission_classes = [permissions.IsAuthenticated]

@api_view(['GET'])
def categorias_egreso(request):
    categorias = Categoria.objects.filter(tipo='EGRESO', activo=True)

    data = [
        {
            'id': c.id,
            'nombre': c.nombre
        }
        for c in categorias
    ]

    return Response(data)