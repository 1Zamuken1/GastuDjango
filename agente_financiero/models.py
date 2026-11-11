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
    bloques = models.JSONField(null=True, blank=True)
    animo = models.CharField(max_length=20, null=True, blank=True)
    procedencia = models.CharField(max_length=100, null=True, blank=True)
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
        """True si deben mostrarse alertas nuevas.

        Reglas:
        1. Período de luna de miel: durante las primeras 3h desde el registro
           del usuario no se muestran alertas (evita conflicto con tutorial/onboarding).
        2. Si nunca se han generado alertas, se muestra (solo si pasó la luna de miel).
        3. Si pasaron >= 6 horas desde la última generación, se genera nueva.
        4. Si no, se devuelve la existente (ventana deslizante de 6h).
        """
        from datetime import timedelta

        ahora = timezone.now()

        # ── Luna de miel: primeras 3h desde el registro ──
        if usuario.date_joined and (ahora - usuario.date_joined).total_seconds() < 3 * 3600:
            return False

        ultima = cls.objects.filter(usuario=usuario).first()

        if not ultima:
            return True

        # ── Ventana deslizante de 6h ──
        return (ahora - ultima.generado_en).total_seconds() >= 6 * 3600

class AccionPendiente(models.Model):
    """
    Cambio que el agente preparo y que solo se aplica si el usuario lo confirma.

    El modelo de lenguaje nunca escribe datos: sus herramientas de escritura crean
    una AccionPendiente y el chat muestra una tarjeta con Confirmar / Cancelar.
    El token es de un solo uso, pertenece a un usuario y vence a los 10 minutos.
    """

    class Tipo(models.TextChoices):
        CREAR_MOVIMIENTO = "CREAR_MOVIMIENTO", "Crear movimiento"
        EDITAR_MOVIMIENTO = "EDITAR_MOVIMIENTO", "Editar movimiento"
        ELIMINAR_MOVIMIENTO = "ELIMINAR_MOVIMIENTO", "Eliminar movimiento"
        ELIMINAR_PRESUPUESTO = "ELIMINAR_PRESUPUESTO", "Eliminar presupuesto"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        CANCELADA = "CANCELADA", "Cancelada"
        FALLIDA = "FALLIDA", "Fallida"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="acciones_agente",
    )
    token = models.CharField(max_length=64, unique=True)
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    datos = models.JSONField(default=dict)
    resumen = models.CharField(max_length=255)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    resuelto_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Acción pendiente del agente"
        verbose_name_plural = "Acciones pendientes del agente"
        indexes = [models.Index(fields=["usuario", "estado"])]

    def __str__(self):
        return f"{self.usuario_id} - {self.tipo} - {self.estado}"

    @property
    def vencida(self) -> bool:
        return timezone.now() >= self.expira_en
