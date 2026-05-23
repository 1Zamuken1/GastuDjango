from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Presupuesto
from .serializer import PresupuestoSerializer
from .services import (
    desactivar_presupuestos_vencidos,
    obtener_estados_presupuestos,
    _qs_con_total_gastado,
)


class PresupuestoViewSet(viewsets.ModelViewSet):
    """CRUD de presupuestos. Incluye acciones extra para alertas y estado combinado."""
    queryset = Presupuesto.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PresupuestoSerializer

    def get_queryset(self):
        """Presupuestos del usuario autenticado con categoría precargada."""
        return Presupuesto.objects.filter(
            usuario=self.request.user
        ).select_related('categoria')

    def perform_create(self, serializer):
        """Asigna el usuario autenticado al crear."""
        serializer.save(usuario=self.request.user)

    @action(detail=False, methods=['get'])
    def alertas(self, request):
        """Retorna el estado de alerta de todos los presupuestos activos del usuario."""
        data = obtener_estados_presupuestos(request.user)
        return Response({"ok": True, "alertas": data})

    @action(detail=False, methods=['get'])
    def con_estado(self, request):
        """Lista completa de presupuestos con datos de gasto y alerta embebidos.

        Combina la respuesta del serializer con los campos calculados
        ``gastado``, ``porcentaje`` y ``alerta`` en un solo endpoint.
        """
        qs = _qs_con_total_gastado(
            Presupuesto.objects.filter(usuario=request.user)
        )
        serializer = self.get_serializer(qs, many=True)
        estados = {a['id']: a for a in obtener_estados_presupuestos(request.user)}
        for item in serializer.data:
            estado = estados.get(item['id'], {})
            item['gastado'] = estado.get('gastado', 0)
            item['porcentaje'] = estado.get('porcentaje', 0)
            item['alerta'] = estado.get('alerta', 'baja')
        return Response({"ok": True, "data": serializer.data})

    @action(detail=False, methods=['post'])
    def verificar_vencidos(self, request):
        """Desactiva presupuestos vencidos y retorna la lista de los afectados."""
        desactivados = desactivar_presupuestos_vencidos(request.user)
        return Response({"ok": True, "desactivados": desactivados})