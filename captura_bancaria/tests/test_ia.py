"""Tests de la lectura con IA (la llamada a Groq se simula)."""
from datetime import datetime
from decimal import Decimal

import pytest

from captura_bancaria.parsers import ia, parsear_correo

TEXTO_DAVIVIENDA = (
    'Davivienda le informa que se realizo una compra con su Tarjeta Debito terminada en 4821 '
    'por valor de $ 27.450 en DROGUERIA CRUZ VERDE el 08/11/2026 a las 19:22.'
)
RESPUESTA_OK = {
    'es_movimiento': True, 'tipo': 'EGRESO', 'operacion': 'compra', 'monto': 27450,
    'comercio': 'DROGUERIA CRUZ VERDE', 'fecha': '2026-11-08 19:22', 'producto': 'T.Deb *4821',
}


@pytest.fixture
def ia_activa(settings, monkeypatch):
    settings.CAPTURA_USAR_IA = True
    settings.GROQ_API_KEY = 'gsk_prueba'
    llamadas = []

    def responder(respuesta):
        def falso(asunto, texto):
            llamadas.append(texto)
            return respuesta
        monkeypatch.setattr(ia, '_llamar_groq', falso)
    responder.llamadas = llamadas
    return responder


def test_banco_generico_se_lee_con_ia(ia_activa):
    ia_activa(RESPUESTA_OK)
    datos = parsear_correo('notificaciones@davivienda.com', 'Compra', TEXTO_DAVIVIENDA)
    assert datos.banco == 'Davivienda'
    assert datos.metodo == 'IA'
    assert datos.monto == Decimal('27450.00')
    assert datos.fecha == datetime(2026, 11, 8, 19, 22)


def test_monto_inventado_se_rechaza(ia_activa):
    ia_activa({**RESPUESTA_OK, 'monto': 99000})
    assert parsear_correo('notificaciones@davivienda.com', 'Compra', TEXTO_DAVIVIENDA) is None


def test_no_movimiento_se_rechaza(ia_activa):
    ia_activa({'es_movimiento': False})
    assert parsear_correo('notificaciones@davivienda.com', 'Clave', 'Tu codigo es 448812') is None


def test_tipo_invalido_se_rechaza(ia_activa):
    ia_activa({**RESPUESTA_OK, 'tipo': 'AHORRO'})
    assert parsear_correo('notificaciones@davivienda.com', 'Compra', TEXTO_DAVIVIENDA) is None


def test_sin_ia_banco_generico_no_se_lee():
    assert parsear_correo('notificaciones@davivienda.com', 'Compra', TEXTO_DAVIVIENDA) is None


def test_bancolombia_formato_desconocido_usa_ia(ia_activa):
    ia_activa({**RESPUESTA_OK, 'monto': 15000, 'comercio': 'PSE EPM'})
    texto = 'Bancolombia: Realizaste un debito automatico de $15.000 para PSE EPM.'
    datos = parsear_correo('alertasynotificaciones@ayn.notificacionesbancolombia.com', 'Alerta', texto)
    assert datos.metodo == 'IA'
    assert datos.banco == 'Bancolombia'


def test_bancolombia_conocido_no_llama_ia(ia_activa):
    ia_activa(RESPUESTA_OK)
    texto = 'Bancolombia: Compraste $45.000 en EXITO COLOMBIA con tu T.Deb *1234, el 09/11/2026 a las 14:32.'
    datos = parsear_correo('alertasynotificaciones@bancolombia.com.co', 'Alerta', texto)
    assert datos.metodo == 'REGLAS'
    assert ia_activa.llamadas == []


def test_clave_dinamica_bancolombia_no_llama_ia(ia_activa):
    ia_activa(RESPUESTA_OK)
    texto = 'Bancolombia: Tu clave dinamica es 482913. No la compartas.'
    assert parsear_correo('alertasynotificaciones@bancolombia.com.co', 'Clave', texto) is None
    assert ia_activa.llamadas == []
