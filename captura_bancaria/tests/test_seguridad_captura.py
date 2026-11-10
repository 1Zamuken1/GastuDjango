"""Tests de seguridad de la captura: correos falsos con HTML y cupo de IA."""
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache

from captura_bancaria import services
from captura_bancaria.models import BuzonCaptura
from captura_bancaria.parsers import ia
from categorias.models import Categoria


@pytest.fixture(autouse=True)
def _sin_websocket(monkeypatch):
    from notificaciones.dispatcher import NotificationDispatcher
    monkeypatch.setattr(NotificationDispatcher, '_push_to_websocket', classmethod(lambda cls, *a, **k: None))
    monkeypatch.setattr(NotificationDispatcher, 'dispatch', classmethod(lambda cls, *a, **k: None))


@pytest.fixture
def buzon(db):
    for nombre in ('Alimentación', 'Otros gastos'):
        Categoria.objects.get_or_create(nombre=nombre, tipo='EGRESO')
    usuario = get_user_model().objects.create_user(username='eva', email='eva@ejemplo.com', password='Clave123!')
    return BuzonCaptura.objects.create(usuario=usuario)


def _correo(remitente, cuerpo, message_id='falso@atacante'):
    return (
        f'From: {remitente}\r\nTo: x@gastu.duckdns.org\r\nSubject: Alerta\r\n'
        f'Message-ID: <{message_id}>\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{cuerpo}\r\n'
    ).encode('utf-8')


def test_limpiar_texto_externo_quita_marcado():
    limpio = services.limpiar_texto_externo('<img src=x onerror=alert(1)> {"bloques":[]} `x`', 120)
    assert '<' not in limpio and '>' not in limpio and '{' not in limpio and '`' not in limpio


def test_correo_falso_con_html_no_guarda_marcado(buzon):
    raw = _correo(
        'atacante@evil.com',
        'Bancolombia le informa Compra por $1.000,00 en <img src=x onerror=alert(1)> 14:32. '
        '09/11/2026 T.Cred *1234.',
    )
    resultado, detectado = services.procesar_correo(raw, buzon.direccion)
    assert detectado is not None, resultado
    assert '<' not in detectado.comercio and '>' not in detectado.comercio
    assert detectado.correo.dkim_valido is False


def test_ia_sin_dkim_respeta_cupo_diario(buzon, settings, monkeypatch):
    settings.CAPTURA_USAR_IA = True
    settings.GROQ_API_KEY = 'gsk_prueba'
    settings.CAPTURA_IA_MAX_SIN_DKIM = 2
    cache.clear()
    llamadas = []

    def falso(asunto, texto):
        llamadas.append(texto)
        return {'es_movimiento': False}

    monkeypatch.setattr(ia, '_llamar_groq', falso)
    for i in range(5):
        # Texto que ningun parser de reglas entiende: cae en la IA del parser generico.
        raw = _correo('alertas@davivienda.com', f'Davivienda aviso numero {i} sin formato conocido', f'm{i}@x')
        services.procesar_correo(raw, buzon.direccion)
    assert len(llamadas) == 2
    assert ia.autorizador_ia.get() is None
