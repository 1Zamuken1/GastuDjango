from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializer import PresupuestoSerializer
from .models import Presupuesto
from .services import obtener_estado_presupuesto


class PresupuestoViewSet(viewsets.ModelViewSet):
    queryset = Presupuesto.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PresupuestoSerializer

    def get_queryset(self):
        return Presupuesto.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)
    @action(detail=False, methods=['get'])
    def alertas(self, request):
        presupuestos = Presupuesto.objects.filter(
            usuario=request.user,
            isActivo=True
        )

        data = [
            obtener_estado_presupuesto(p)
            for p in presupuestos
        ]

        return Response({
            "ok": True,
            "alertas": data
        })