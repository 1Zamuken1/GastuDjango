from django.db import models
from django.conf import settings
from django.utils import timezone


class MensajeChat(models.Model):
    """Mensaje individual del chat entre el usuario y el agente financiero (GASTU)."""
    ROL_CHOICES = [
        ("user", "Usuario"),
        ("bot", "Agente"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="mensajes_chat", db_index=True,
    )
    rol = models.CharField(max_length=10, choices=ROL_CHOICES)
    contenido = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["creado_en"]
        indexes = [
            models.Index(fields=['usuario', '-creado_en']),
        ]

    def __str__(self):
        return f"[{self.usuario.username}] {self.rol} — {self.creado_en:%d/%m/%Y %H:%M}"


class AlertaDiaria(models.Model):
    """Registra cuándo se generaron y mostraron las alertas a un usuario.

    Se usa para controlar la frecuencia de aparición del modal (máx 1 vez cada 6 h).
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="alertas_diarias", db_index=True,
    )
    alertas_json = models.JSONField()
    generado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    visto_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-generado_en"]
        indexes = [
            models.Index(fields=['usuario', '-generado_en']),
        ]

    def __str__(self):
        return f"[{self.usuario.username}] Alertas — {self.generado_en:%d/%m/%Y %H:%M}"

    @classmethod
    def debe_mostrar(cls, usuario) -> bool:
        """True si deben mostrarse alertas nuevas: nunca mostradas o pasaron >6 h desde la última."""
        from datetime import timedelta

        ahora = timezone.now()
        hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        ultima = cls.objects.filter(usuario=usuario).first()

        if not ultima:
            return True

        if ultima.generado_en >= hoy_inicio:
            if (ahora - ultima.generado_en).total_seconds() < 6 * 3600:
                return False

        return True