"""URLs del API REST para agente_financiero."""

from django.urls import path
from .api_views import chat_view, limpiar_view
from .alertas_views import alertas_view

urlpatterns = [
    path("agente/chat/", chat_view, name="agente_chat"),
    path("agente/limpiar/", limpiar_view, name="agente_limpiar"),
    path("agente/alertas/", alertas_view, name="agente_alertas"),
]