from rest_framework import viewsets, permissions
from .models import Categoria, CategoriaFavorita
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers
from django.db.models import Count, Q, Exists, OuterRef
from django.shortcuts import get_object_or_404

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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_favorita(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk, activo=True)
    fav, created = CategoriaFavorita.objects.get_or_create(usuario=request.user, categoria=categoria)
    if not created:
        fav.delete()
        es_favorita = False
    else:
        es_favorita = True
    return Response({'es_favorita': es_favorita, 'id': categoria.id})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def categorias_enriched(request):
    tipo = request.GET.get('tipo', None)
    actividad = request.GET.get('actividad', 'false') == 'true'
    
    qs = Categoria.objects.filter(activo=True, es_sistema=False)
    
    if tipo and tipo != 'todas' and tipo != '':
        qs = qs.filter(tipo=tipo)
        
    if actividad:
        # Solo categorias con movimientos o metas de ahorro de este usuario
        from movimientos.models import Movimiento
        from ahorros.models import AhorroMeta
        
        movs = Movimiento.objects.filter(usuario=request.user, categoria=OuterRef('pk'))
        ahorros = AhorroMeta.objects.filter(usuario=request.user, categoria=OuterRef('pk'))
        qs = qs.annotate(
            tiene_mov=Exists(movs),
            tiene_ahorro=Exists(ahorros)
        ).filter(Q(tiene_mov=True) | Q(tiene_ahorro=True))
        
    fav_subquery = CategoriaFavorita.objects.filter(usuario=request.user, categoria=OuterRef('pk'))
    
    # We order by uso_global descending if actividad=true, else by name
    qs = qs.annotate(
        es_favorita=Exists(fav_subquery),
        uso_global=Count('movimientos')
    )
    
    if actividad:
        qs = qs.order_by('-uso_global', 'nombre')
    else:
        qs = qs.order_by('nombre')
    
    data = [
        {
            'id': c.id,
            'nombre': c.nombre,
            'tipo': c.tipo,
            'es_favorita': c.es_favorita,
            'uso_global': c.uso_global
        }
        for c in qs
    ]
    return Response(data)