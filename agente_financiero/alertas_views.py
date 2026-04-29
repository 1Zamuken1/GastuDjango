"""
agente_financiero/alertas_views.py

Vista para el endpoint de alertas diarias.
Controla la frecuencia de generación y las guarda en BD.
"""

import logging
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import AlertaDiaria
from .alertas_service import generar_alertas

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class AlertasView(View):

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"ok": False, "error": "No autenticado."}, status=401)

        ultima = AlertaDiaria.objects.filter(usuario=request.user).first()

        # Si ya existe una vigente (< 6h) → servir desde BD sin llamar a Groq
        if ultima and not AlertaDiaria.debe_mostrar(request.user):
            return JsonResponse({
                "ok": True,
                "mostrar": True,
                "alertas": ultima.alertas_json,
                "registro_id": ultima.id,
            })

        # No existe o ya expiró → generar nuevas con Groq
        try:
            alertas = generar_alertas(request.user)
        except Exception as e:
            logger.error(f"[GASTU Alertas] Error generando alertas para {request.user.id}: {e}")
            return JsonResponse({"ok": False, "error": "Error al generar alertas."}, status=500)

        if not alertas:
            return JsonResponse({"ok": True, "mostrar": False, "alertas": []})

        registro = AlertaDiaria.objects.create(
            usuario=request.user,
            alertas_json=alertas,
        )

        return JsonResponse({
            "ok": True,
            "mostrar": True,
            "alertas": alertas,
            "registro_id": registro.id,
        })

    def post(self, request, *args, **kwargs):
        """
        Marca las alertas como vistas (el usuario cerró el modal).
        Body: {"registro_id": 123}
        """
        if not request.user.is_authenticated:
            return JsonResponse({"ok": False, "error": "No autenticado."}, status=401)

        import json
        try:
            body = json.loads(request.body)
            registro_id = body.get("registro_id")
        except Exception:
            return JsonResponse({"ok": False, "error": "Body inválido."}, status=400)

        if registro_id:
            AlertaDiaria.objects.filter(
                id=registro_id,
                usuario=request.user,
                visto_en__isnull=True,
            ).update(visto_en=timezone.now())

        return JsonResponse({"ok": True})


alertas_view = AlertasView.as_view()