from rest_framework import viewsets, permissions
from .models import Programacion
from .serializers import ProgramacionSerializer



class ProgramacionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = ProgramacionSerializer

    def get_queryset(self):
        return Programacion.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)