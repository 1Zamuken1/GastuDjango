from django.db import models
from django.conf import settings


class MensajeChat(models.Model):
    ROL_CHOICES = [
        ("user", "Usuario"),
        ("bot", "Agente"),
    ]

    usuario    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mensajes_chat")
    rol        = models.CharField(max_length=10, choices=ROL_CHOICES)
    contenido  = models.TextField()
    creado_en  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creado_en"]

    def __str__(self):
        return f"[{self.usuario.username}] {self.rol} — {self.creado_en:%d/%m/%Y %H:%M}"