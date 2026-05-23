from rest_framework import viewsets, permissions

from .models import Programacion
from .serializers import ProgramacionSerializer


class ProgramacionViewSet(viewsets.ModelViewSet):
    """CRUD estándar de programaciones. Filtra por usuario autenticado."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProgramacionSerializer

    def get_queryset(self):
        """Retorna las programaciones del usuario con la categoría precargada."""
        return Programacion.objects.filter(
            usuario=self.request.user
        ).select_related('categoria')

    def perform_create(self, serializer):
        """Asigna automáticamente el usuario autenticado al crear."""
        serializer.save(usuario=self.request.user)