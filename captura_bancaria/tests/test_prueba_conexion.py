"""Tests de la prueba de conexion y de la deteccion del reenvio automatico."""
from datetime import timedelta
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from captura_bancaria import services
from captura_bancaria.models import BuzonCaptura, MovimientoDetectado
from categorias.models import Categoria

CORREOS = Path(__file__).parent / 'correos'


@pytest.fixture(autouse=True)
def _sin_websocket(monkeypatch):
    from notificaciones.dispatcher import NotificationDispatcher
    monkeypatch.setattr(NotificationDispatcher, '_push_to_websocket', classmethod(lambda cls, *a, **k: None))
    monkeypatch.setattr(NotificationDispatcher, 'dispatch', classmethod(lambda cls, *a, **k: None))
    monkeypatch.setattr(services, '_avisar_prueba', lambda usuario_id: None)


@pytest.fixture
def buzon(db):
    for nombre in ('Otros gastos', 'Alimentación'):
        Categoria.objects.get_or_create(nombre=nombre, tipo='EGRESO')
    usuario = get_user_model().objects.create_user(username='ana', email='ana@ejemplo.com', password='Clave123!')
    return BuzonCaptura.objects.create(usuario=usuario)


def _correo(asunto, cuerpo='Hola', remitente='ana@gmail.com', cabeceras=''):
    return (f'From: {remitente}\r\nSubject: {asunto}\r\nMessage-ID: <{asunto}@x>\r\n{cabeceras}\r\n{cuerpo}').encode()


def test_correo_con_codigo_completa_la_prueba(buzon):
    codigo = services.iniciar_prueba(buzon)
    assert codigo.startswith('GASTU-') and len(codigo) == 12
    assert services.estado_prueba(buzon)['estado'] == 'ESPERANDO'

    resultado, detectado = services.procesar_correo(_correo(f'Prueba {codigo}'), buzon.direccion)
    assert resultado == services.Resultado.PRUEBA_CONEXION
    assert detectado is None

    buzon.refresh_from_db()
    estado = services.estado_prueba(buzon)
    assert estado['estado'] == 'RECIBIDA'
    assert estado['remitente'] == 'ana@gmail.com'
    assert MovimientoDetectado.objects.count() == 0


def test_codigo_en_el_cuerpo_tambien_sirve(buzon):
    codigo = services.iniciar_prueba(buzon)
    resultado, _ = services.procesar_correo(_correo('Hola', cuerpo=f'mi codigo es {codigo.lower()}'), buzon.direccion)
    assert resultado == services.Resultado.PRUEBA_CONEXION


def test_codigo_vencido_no_cuenta(buzon):
    codigo = services.iniciar_prueba(buzon)
    BuzonCaptura.objects.filter(pk=buzon.pk).update(prueba_creada_en=timezone.now() - timedelta(minutes=31))
    buzon.refresh_from_db()
    assert services.estado_prueba(buzon)['estado'] == 'VENCIDA'
    resultado, _ = services.procesar_correo(_correo(f'Prueba {codigo}'), buzon.direccion)
    assert resultado == services.Resultado.IGNORADO


def test_codigo_viejo_deja_de_servir_al_generar_otro(buzon):
    viejo = services.iniciar_prueba(buzon)
    services.iniciar_prueba(buzon)
    buzon.refresh_from_db()
    resultado, _ = services.procesar_correo(_correo(f'Prueba {viejo}'), buzon.direccion)
    assert resultado == services.Resultado.IGNORADO


def test_alerta_reenviada_por_filtro_marca_reenvio_automatico(buzon):
    raw = (CORREOS / 'compra_tarjeta.eml').read_bytes()
    services.procesar_correo(raw, buzon.direccion)
    buzon.refresh_from_db()
    assert buzon.reenvio_automatico_en is None

    reenviado = b'X-Forwarded-For: ana@gmail.com ' + buzon.direccion.encode() + b'\r\nX-Forwarded-To: ' \
        + buzon.direccion.encode() + b'\r\n' + raw.replace(b'compra_tarjeta.eml@', b'reenviado@')
    reenviado = reenviado.replace(b'14:32', b'15:10')
    services.procesar_correo(reenviado, buzon.direccion)
    buzon.refresh_from_db()
    assert buzon.reenvio_automatico_en is not None


def test_api_prueba(buzon):
    c = Client()
    c.force_login(buzon.usuario)
    assert c.get(reverse('captura_bancaria:api_prueba')).json()['prueba']['estado'] == 'SIN_PRUEBA'
    r = c.post(reverse('captura_bancaria:api_prueba')).json()
    assert r['prueba']['estado'] == 'ESPERANDO'
    assert r['direccion'] == buzon.direccion
    services.procesar_correo(_correo(r['prueba']['codigo']), buzon.direccion)
    r = c.get(reverse('captura_bancaria:api_prueba')).json()
    assert r['prueba']['estado'] == 'RECIBIDA'
    resumen = c.get(reverse('captura_bancaria:api_resumen')).json()
    assert resumen['prueba']['estado'] == 'RECIBIDA'
