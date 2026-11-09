"""Tests de servicios y API de la captura bancaria."""
import json
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.urls import reverse

from captura_bancaria import services
from captura_bancaria.models import BuzonCaptura, CorreoEntrante, MovimientoDetectado, ReglaComercio
from categorias.models import Categoria
from movimientos.models import Movimiento
from notificaciones.models import Notificacion

CORREOS = Path(__file__).parent / 'correos'
TOKEN = 'token-de-prueba'


@pytest.fixture(autouse=True)
def _sin_websocket(monkeypatch):
    """Evita depender del channel layer en los tests."""
    from notificaciones.dispatcher import NotificationDispatcher
    monkeypatch.setattr(NotificationDispatcher, '_push_to_websocket', classmethod(lambda cls, *a, **k: None))
    monkeypatch.setattr(NotificationDispatcher, 'dispatch', classmethod(lambda cls, *a, **k: None))


@pytest.fixture
def categorias(db):
    nombres = {
        'EGRESO': ['Alimentación', 'Vivienda', 'Otros gastos'],
        'INGRESO': ['Salario', 'Transferencias', 'Otros ingresos'],
    }
    for tipo, lista in nombres.items():
        for nombre in lista:
            Categoria.objects.get_or_create(nombre=nombre, tipo=tipo)


@pytest.fixture
def usuario(db):
    return get_user_model().objects.create_user(username='ana', email='ana@ejemplo.com', password='Clave123!')


@pytest.fixture
def buzon(usuario):
    return BuzonCaptura.objects.create(usuario=usuario)


def _raw(nombre):
    return (CORREOS / nombre).read_bytes()


def test_procesar_compra_crea_pendiente_y_notificacion(categorias, buzon):
    resultado, detectado = services.procesar_correo(_raw('compra_tarjeta.eml'), buzon.direccion)

    assert resultado == services.Resultado.DETECTADO
    assert detectado.estado == MovimientoDetectado.Estado.PENDIENTE
    assert detectado.monto == Decimal('45000.00')
    assert detectado.categoria_sugerida.nombre == 'Alimentación'
    assert Notificacion.objects.filter(
        usuario=buzon.usuario, tipo=Notificacion.Tipo.MOVIMIENTO_DETECTADO, referencia_id=detectado.id,
    ).exists()
    buzon.refresh_from_db()
    assert buzon.verificado
    assert Movimiento.objects.count() == 0


def test_alias_desconocido(categorias, buzon):
    resultado, _ = services.procesar_correo(_raw('compra_tarjeta.eml'), 'noexiste@gastu.duckdns.org')
    assert resultado == services.Resultado.BUZON_NO_EXISTE


def test_mismo_correo_dos_veces_no_duplica(categorias, buzon):
    services.procesar_correo(_raw('compra_tarjeta.eml'), buzon.direccion)
    resultado, _ = services.procesar_correo(_raw('compra_tarjeta.eml'), buzon.direccion)
    assert resultado == services.Resultado.DUPLICADO
    assert MovimientoDetectado.objects.count() == 1


def test_misma_alerta_con_otro_message_id_no_duplica(categorias, buzon):
    raw = _raw('compra_tarjeta.eml')
    services.procesar_correo(raw, buzon.direccion)
    otro = raw.replace(b'compra_tarjeta.eml@ejemplo', b'reenvio-manual@ejemplo')
    resultado, _ = services.procesar_correo(otro, buzon.direccion)
    assert resultado == services.Resultado.DUPLICADO
    assert MovimientoDetectado.objects.count() == 1


def test_verificacion_gmail_guarda_codigo(categorias, buzon):
    resultado, _ = services.procesar_correo(_raw('verificacion_gmail.eml'), buzon.direccion)
    assert resultado == services.Resultado.VERIFICACION_GMAIL
    buzon.refresh_from_db()
    assert buzon.codigo_reenvio_gmail == '123456789'
    assert buzon.enlace_reenvio_gmail.startswith('https://mail-settings.google.com/')
    assert not buzon.verificado


def test_correo_no_bancario_se_ignora(categorias, buzon):
    raw = b'From: amigo@gmail.com\r\nSubject: Hola\r\nMessage-ID: <x@y>\r\n\r\nNos vemos el viernes.'
    resultado, _ = services.procesar_correo(raw, buzon.direccion)
    assert resultado == services.Resultado.IGNORADO
    assert CorreoEntrante.objects.get().estado == CorreoEntrante.Estado.IGNORADO


def test_confirmar_crea_movimiento_y_aprende_regla(categorias, buzon):
    _, detectado = services.procesar_correo(_raw('compra_tarjeta.eml'), buzon.direccion)
    vivienda = Categoria.objects.get(nombre='Vivienda')

    movimiento, advertencia = services.confirmar(detectado, buzon.usuario, categoria=vivienda)

    assert movimiento.categoria == vivienda
    assert movimiento.monto == Decimal('45000.00')
    assert movimiento.fecha_registro == detectado.fecha_transaccion
    assert advertencia  # sin ingresos previos, el egreso supera el disponible
    detectado.refresh_from_db()
    assert detectado.estado == MovimientoDetectado.Estado.CONFIRMADO
    regla = ReglaComercio.objects.get(usuario=buzon.usuario)
    assert regla.comercio_normalizado == 'exito colombia'
    assert regla.categoria == vivienda


def test_regla_aprendida_se_usa_en_siguiente_deteccion(categorias, buzon):
    _, primero = services.procesar_correo(_raw('compra_tarjeta.eml'), buzon.direccion)
    services.confirmar(primero, buzon.usuario, categoria=Categoria.objects.get(nombre='Vivienda'))

    texto = 'Bancolombia le informa Compra por $9.900 en EXITO COLOMBIA 18:00. 08/11/2026 T.Cred *1234.'
    raw = f'From: alertasynotificaciones@bancolombia.com.co\r\nSubject: Alerta\r\n\r\n{texto}'.encode()
    _, segundo = services.procesar_correo(raw, buzon.direccion)
    assert segundo.categoria_sugerida.nombre == 'Vivienda'


def test_auto_confirmar_requiere_dkim(categorias, buzon):
    _, primero = services.procesar_correo(_raw('compra_tarjeta.eml'), buzon.direccion)
    services.confirmar(primero, buzon.usuario, auto_confirmar=True)

    texto = 'Bancolombia le informa Compra por $9.900 en EXITO COLOMBIA 18:00. 08/11/2026 T.Cred *1234.'
    raw = f'From: alertasynotificaciones@bancolombia.com.co\r\nSubject: Alerta\r\n\r\n{texto}'.encode()
    resultado, segundo = services.procesar_correo(raw, buzon.direccion)
    # Sin firma DKIM valida queda pendiente aunque la regla diga auto_confirmar.
    assert resultado == services.Resultado.DETECTADO
    assert segundo.estado == MovimientoDetectado.Estado.PENDIENTE


def test_no_se_confirma_dos_veces(categorias, buzon):
    _, detectado = services.procesar_correo(_raw('compra_tarjeta.eml'), buzon.direccion)
    services.confirmar(detectado, buzon.usuario)
    with pytest.raises(services.ErrorCaptura):
        services.confirmar(detectado, buzon.usuario)
    assert Movimiento.objects.count() == 1


def test_categoria_de_otro_tipo_se_rechaza(categorias, buzon):
    _, detectado = services.procesar_correo(_raw('compra_tarjeta.eml'), buzon.direccion)
    with pytest.raises(services.ErrorCaptura):
        services.confirmar(detectado, buzon.usuario, categoria=Categoria.objects.get(nombre='Salario'))


def test_ingreso_nomina_sugiere_salario(categorias, buzon):
    _, detectado = services.procesar_correo(_raw('nomina.eml'), buzon.direccion)
    assert detectado.tipo == 'INGRESO'
    assert detectado.categoria_sugerida.nombre == 'Salario'


# ── API ─────────────────────────────────────────────────────────

@override_settings(CAPTURA_INGESTA_TOKEN=TOKEN)
def test_ingesta_requiere_token(categorias, buzon):
    c = Client()
    url = reverse('captura_bancaria:ingesta')
    r = c.post(url, data=_raw('compra_tarjeta.eml'), content_type='message/rfc822',
               HTTP_X_CAPTURA_TOKEN='malo', HTTP_X_CAPTURA_DESTINATARIO=buzon.direccion)
    assert r.status_code == 403

    r = c.post(url, data=_raw('compra_tarjeta.eml'), content_type='message/rfc822',
               HTTP_X_CAPTURA_TOKEN=TOKEN, HTTP_X_CAPTURA_DESTINATARIO=buzon.direccion)
    assert r.status_code == 200
    assert r.json()['resultado'] == 'DETECTADO'

    r = c.post(url, data=_raw('retiro.eml'), content_type='message/rfc822',
               HTTP_X_CAPTURA_TOKEN=TOKEN, HTTP_X_CAPTURA_DESTINATARIO='nadie@gastu.duckdns.org')
    assert r.status_code == 404


def test_api_flujo_usuario(categorias, usuario):
    c = Client()
    c.force_login(usuario)

    r = c.post(reverse('captura_bancaria:api_buzon'))
    assert r.json()['buzon']['activo']
    buzon = BuzonCaptura.objects.get(usuario=usuario)

    services.procesar_correo(_raw('compra_tarjeta.eml'), buzon.direccion)
    services.procesar_correo(_raw('retiro.eml'), buzon.direccion)
    services.procesar_correo(_raw('transferencia_recibida.eml'), buzon.direccion)

    r = c.get(reverse('captura_bancaria:api_detectados'))
    pendientes = r.json()['detectados']
    assert len(pendientes) == 3

    r = c.post(reverse('captura_bancaria:api_descartar', args=[pendientes[0]['id']]))
    assert r.json()['ok']

    ids = [p['id'] for p in pendientes[1:]]
    r = c.post(reverse('captura_bancaria:api_confirmar_lote'), data=json.dumps({'ids': ids}),
               content_type='application/json')
    assert sorted(r.json()['confirmados']) == sorted(ids)
    assert Movimiento.objects.filter(usuario=usuario).count() == 2


def test_api_no_expone_detectados_de_otro_usuario(categorias, buzon):
    _, detectado = services.procesar_correo(_raw('compra_tarjeta.eml'), buzon.direccion)
    intruso = get_user_model().objects.create_user(username='eva', email='eva@ejemplo.com', password='Clave123!')
    c = Client()
    c.force_login(intruso)
    r = c.post(reverse('captura_bancaria:api_confirmar', args=[detectado.id]),
               data='{}', content_type='application/json')
    assert r.status_code == 404
    assert c.get(reverse('captura_bancaria:api_detectados')).json()['detectados'] == []


def test_regenerar_alias_invalida_direccion_anterior(categorias, buzon):
    anterior = buzon.direccion
    buzon.regenerar_alias()
    resultado, _ = services.procesar_correo(_raw('compra_tarjeta.eml'), anterior)
    assert resultado == services.Resultado.BUZON_NO_EXISTE


def test_pagina_requiere_login(db):
    r = Client().get(reverse('captura_bancaria:captura'))
    assert r.status_code == 302


def test_api_resumen_historial_y_reglas(categorias, usuario):
    c = Client()
    c.force_login(usuario)
    r = c.get(reverse('captura_bancaria:api_resumen')).json()
    assert r['buzon']['activo'] is False
    assert r['pasos'] == {'direccion': False, 'reenvio_gmail': False, 'primera_alerta': False}
    assert 'Bancolombia' in r['bancos']

    c.post(reverse('captura_bancaria:api_buzon'))
    buzon = BuzonCaptura.objects.get(usuario=usuario)
    services.procesar_correo(_raw('verificacion_gmail.eml'), buzon.direccion)
    _, compra = services.procesar_correo(_raw('compra_tarjeta.eml'), buzon.direccion)
    services.procesar_correo(_raw('retiro.eml'), buzon.direccion)

    r = c.get(reverse('captura_bancaria:api_resumen')).json()
    assert r['pasos'] == {'direccion': True, 'reenvio_gmail': True, 'primera_alerta': True}
    assert r['estadisticas']['pendientes'] == 2
    assert r['estadisticas']['egresos_pendientes'] == '$245.000'

    r = c.get(reverse('captura_bancaria:api_detectados') + '?limite=1').json()
    assert r['total'] == 2 and len(r['detectados']) == 1

    c.post(reverse('captura_bancaria:api_confirmar', args=[compra.id]), data='{}', content_type='application/json')
    historial = c.get(reverse('captura_bancaria:api_detectados') + '?estado=HISTORIAL').json()['detectados']
    assert [d['id'] for d in historial] == [compra.id]
    assert historial[0]['estado'] == 'CONFIRMADO'

    reglas = c.get(reverse('captura_bancaria:api_reglas')).json()['reglas']
    assert len(reglas) == 1 and reglas[0]['auto_confirmar'] is False
    rid = reglas[0]['id']
    r = c.post(reverse('captura_bancaria:api_regla_actualizar', args=[rid]),
               data=json.dumps({'auto_confirmar': True}), content_type='application/json').json()
    assert r['regla']['auto_confirmar'] is True
    c.post(reverse('captura_bancaria:api_regla_eliminar', args=[rid]))
    assert not ReglaComercio.objects.filter(pk=rid).exists()


def test_reglas_de_otro_usuario_no_se_pueden_tocar(categorias, buzon):
    _, d = services.procesar_correo(_raw('compra_tarjeta.eml'), buzon.direccion)
    services.confirmar(d, buzon.usuario)
    regla = ReglaComercio.objects.get()
    intruso = get_user_model().objects.create_user(username='eva', email='eva@ejemplo.com', password='Clave123!')
    c = Client()
    c.force_login(intruso)
    r = c.post(reverse('captura_bancaria:api_regla_eliminar', args=[regla.id]))
    assert r.status_code == 404
    assert ReglaComercio.objects.filter(pk=regla.id).exists()
