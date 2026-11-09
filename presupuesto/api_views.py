from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from .models import Presupuesto
from .serializer import PresupuestoSerializer
from .services import (
    desactivar_presupuestos_vencidos,
    obtener_estado_presupuesto,
    obtener_estados_presupuestos,
    renovar_presupuesto,
    RenovacionError,
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
        presupuestos = list(_qs_con_total_gastado(
            Presupuesto.objects.filter(usuario=request.user)
        ).order_by('-is_activo', 'fecha_fin'))
        data = []
        for presupuesto, item in zip(presupuestos, self.get_serializer(presupuestos, many=True).data):
            estado = obtener_estado_presupuesto(presupuesto)
            for campo in ('gastado', 'porcentaje', 'alerta', 'disponible', 'dias_restantes', 'gasto_diario'):
                item[campo] = estado[campo]
            data.append(item)
        return Response({"ok": True, "data": data})

    @action(detail=True, methods=['post'])
    def renovar(self, request, pk=None):
        """Crea el presupuesto del período siguiente con la misma categoría y límite."""
        try:
            nuevo = renovar_presupuesto(self.get_object())
        except RenovacionError as error:
            return Response({"ok": False, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"ok": True, "data": self.get_serializer(nuevo).data}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def verificar_vencidos(self, request):
        """Desactiva presupuestos vencidos y retorna la lista de los afectados."""
        desactivados = desactivar_presupuestos_vencidos(request.user)
        return Response({"ok": True, "desactivados": desactivados})