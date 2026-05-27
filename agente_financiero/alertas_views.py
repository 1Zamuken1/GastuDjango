"""Endpoint de alertas diarias. Controla frecuencia de generación y guarda en BD."""

import json
import logging

from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .alertas_service import generar_alertas
from .models import AlertaDiaria

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class AlertasView(View):
    """API de alertas financieras diarias (GET para obtener, POST para marcar como vistas)."""

    def get(self, request, *args, **kwargs):
        """Retorna alertas vigentes de BD (si <6 h) o genera nuevas con Groq."""
        if not request.user.is_authenticated:
            return JsonResponse({"ok": False, "error": "No autenticado."}, status=401)

        if not AlertaDiaria.debe_mostrar(request.user):
            ultima = AlertaDiaria.objects.filter(usuario=request.user).first()
            if ultima:
                return JsonResponse({
                    "ok": True, "mostrar": True,
                    "alertas": ultima.alertas_json, "registro_id": ultima.id,
                })
            return JsonResponse({"ok": True, "mostrar": False, "alertas": []})

        try:
            alertas = generar_alertas(request.user)
        except Exception as e:
            logger.error(f"[GASTU Alertas] Error generando alertas para {request.user.id}: {e}")
            return JsonResponse({"ok": False, "error": "Error al generar alertas."}, status=500)

        if not alertas:
            return JsonResponse({"ok": True, "mostrar": False, "alertas": []})

        registro = AlertaDiaria.objects.create(usuario=request.user, alertas_json=alertas)
        return JsonResponse({
            "ok": True, "mostrar": True,
            "alertas": alertas, "registro_id": registro.id,
        })

    def post(self, request, *args, **kwargs):
        """Marca una alerta como vista. Body: {"registro_id": 123}."""
        if not request.user.is_authenticated:
            return JsonResponse({"ok": False, "error": "No autenticado."}, status=401)

        try:
            body = json.loads(request.body)
            registro_id = body.get("registro_id")
        except Exception:
            return JsonResponse({"ok": False, "error": "Body inválido."}, status=400)

        if registro_id:
            AlertaDiaria.objects.filter(
                id=registro_id, usuario=request.user, visto_en__isnull=True,
            ).update(visto_en=timezone.now())

        return JsonResponse({"ok": True})


alertas_view = AlertasView.as_view()