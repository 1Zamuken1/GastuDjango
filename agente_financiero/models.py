from django.db import models
from django.conf import settings
from django.utils import timezone

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

class AlertaDiaria(models.Model):
    """
    Registra cuándo se generaron y mostraron las alertas a un usuario.
    Se usa para controlar la frecuencia de aparición del modal.
    """
    usuario        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alertas_diarias")
    alertas_json   = models.JSONField()                          # Lista de alertas generadas
    generado_en    = models.DateTimeField(auto_now_add=True)     # Cuándo se generaron
    visto_en       = models.DateTimeField(null=True, blank=True) # Cuándo las vio el usuario
 
    class Meta:
        ordering = ["-generado_en"]
 
    def __str__(self):
        return f"[{self.usuario.username}] Alertas — {self.generado_en:%d/%m/%Y %H:%M}"
 
    @classmethod
    def debe_mostrar(cls, usuario) -> bool:
        """
        Retorna True si se deben mostrar alertas nuevas al usuario.
        Regla: mostrar si nunca se ha mostrado, o si:
          - Han pasado más de 6 horas desde la última vez, Y
          - No se han mostrado hoy todavía (o si se mostraron hace más de 6h)
        """
        from datetime import timedelta
        ahora = timezone.now()
        hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
 
        ultima = cls.objects.filter(usuario=usuario).first()
 
        if not ultima:
            return True  # Nunca se ha mostrado
 
        # Si ya se mostraron hoy y hace menos de 6 horas → no mostrar
        if ultima.generado_en >= hoy_inicio:
            tiempo_transcurrido = ahora - ultima.generado_en
            if tiempo_transcurrido.total_seconds() < 6 * 3600:
                return False
 
        return True  # Pasaron más de 6h o es un nuevo día