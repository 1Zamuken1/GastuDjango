"""
agente_financiero/api_urls.py

Rutas del módulo agente_financiero.
Se registra en gastu_django/urls.py con:
    path('api/', include('agente_financiero.api_urls')),
"""

from django.urls import path
from .api_views import chat_view,limpiar_view

urlpatterns = [
    path("agente/chat/", chat_view, name="agente_chat"),
     path("agente/limpiar/", limpiar_view, name="agente_limpiar"),
]