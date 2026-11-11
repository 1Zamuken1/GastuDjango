"""Tests de los parsers de alertas bancarias (sin base de datos)."""
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from captura_bancaria.parsers import bancolombia, parsear_correo
from captura_bancaria.parsers.base import normalizar_comercio, parsear_monto
from captura_bancaria.services import extraer_texto, leer_correo

CORREOS = Path(__file__).parent / 'correos'


def _parsear_eml(nombre):
    msg = leer_correo((CORREOS / nombre).read_bytes())
    return parsear_correo(str(msg['From']), str(msg['Subject']), extraer_texto(msg))


@pytest.mark.parametrize('texto,esperado', [
    ('45.000', Decimal('45000')),
    ('45.000,50', Decimal('45000.50')),
    ('150,000', Decimal('150000')),
    ('150,000.00', Decimal('150000.00')),
    ('2.500.000', Decimal('2500000')),
    ('1234', Decimal('1234')),
    ('80,5', Decimal('80.5')),
    ('0', None),
])
def test_parsear_monto(texto, esperado):
    assert parsear_monto(texto) == esperado


@pytest.mark.parametrize('archivo,tipo,operacion,monto,comercio', [
    ('compra_tarjeta.eml', 'EGRESO', 'compra', '45000.00', 'EXITO COLOMBIA'),
    ('transferencia_recibida.eml', 'INGRESO', 'transferencia', '150000', 'JUAN PEREZ'),
    ('transferencia_enviada.eml', 'EGRESO', 'transferencia', '50000', 'Transferencia a cuenta *9876'),
    ('pago_servicio.eml', 'EGRESO', 'pago', '80500', 'CLARO COLOMBIA'),
    ('retiro.eml', 'EGRESO', 'retiro', '200000', 'ATM PARQUE LLERAS'),
    ('nomina.eml', 'INGRESO', 'abono', '2500000', 'Abono de nomina'),
])
def test_bancolombia_movimientos(archivo, tipo, operacion, monto, comercio):
    datos = _parsear_eml(archivo)
    assert datos is not None
    assert datos.banco == 'Bancolombia'
    assert datos.tipo == tipo
    assert datos.operacion == operacion
    assert datos.monto == Decimal(monto)
    assert datos.comercio == comercio


def test_bancolombia_fecha_y_producto():
    datos = _parsear_eml('compra_tarjeta.eml')
    assert datos.fecha == datetime(2026, 11, 9, 14, 32)
    assert datos.producto == 'T.Cred *1234'


def test_bancolombia_formato_real_html_con_publicidad():
    """Formato real recibido el 2026-11-09 (cuentas anonimizadas)."""
    datos = _parsear_eml('real_transferencia_enviada.eml')
    assert datos.tipo == 'EGRESO'
    assert datos.operacion == 'transferencia'
    assert datos.monto == Decimal('38000.00')
    assert datos.comercio == 'Transferencia a cuenta *4567'
    assert datos.producto == 'cuenta *1111'
    assert datos.fecha == datetime(2026, 11, 9, 4, 53)


def test_transferencias_a_cuentas_distintas_no_comparten_regla():
    a = normalizar_comercio('Transferencia a cuenta *4567')
    b = normalizar_comercio('Transferencia a cuenta *9999')
    assert a == 'transferencia a cuenta cta4567'
    assert a != b


def test_bancolombia_ignora_clave_dinamica():
    assert _parsear_eml('clave_dinamica.eml') is None


def test_remitente_no_bancario_no_se_parsea():
    assert parsear_correo('amigo@gmail.com', 'Hola', 'Te debo $20.000 del almuerzo') is None


def test_reenvio_manual_detecta_banco_por_texto():
    texto = 'Bancolombia le informa Compra por $12.000 en D1 SUBA 09:10. 01/11/2026 T.Deb *1111.'
    assert bancolombia.es_remitente('yo@gmail.com', texto)
    datos = parsear_correo('yo@gmail.com', 'Fwd: Alertas', texto)
    assert datos.comercio == 'D1 SUBA'


def test_normalizar_comercio():
    assert normalizar_comercio('ÉXITO Colombia 123') == 'exito colombia'
