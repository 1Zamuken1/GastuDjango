"""Tests de las correcciones de calendario, edición y ejecución de programaciones."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from dateutil.relativedelta import relativedelta
from django.test import Client
from django.utils import timezone

from categorias.models import Categoria
from movimientos.models import Movimiento
from programaciones.models import Programacion
from programaciones.services import (
    monto_mensual_estimado,
    obtener_pendientes,
    ocurrencia,
    primera_ocurrencia_desde,
    proxima_inicial,
)
from usuarios.models import Usuario


@pytest.fixture
def usuario():
    return Usuario.objects.create_user(email="mejoras@example.com", password="pass1234", username="mejoras")


@pytest.fixture
def cat_egreso():
    return Categoria.objects.create(nombre="Arriendo prueba", tipo="EGRESO")


@pytest.fixture
def cat_ingreso():
    return Categoria.objects.create(nombre="Salario prueba", tipo="INGRESO")


@pytest.fixture
def client_auto(usuario):
    c = Client()
    c.force_login(usuario)
    return c


@pytest.fixture
def prog_activa(usuario, cat_egreso):
    return Programacion.objects.create(
        monto_programado=Decimal("100000"), tipo="EGRESO", descripcion="Arriendo",
        fecha_inicio=date.today() - timedelta(days=30), fecha_fin=date.today() + timedelta(days=60),
        frecuencia="MENSUAL", proxima_ejecucion=date.today(), activo=True,
        categoria=cat_egreso, usuario=usuario,
    )


@pytest.fixture
def con_saldo(usuario):
    cat = Categoria.objects.create(nombre="Sueldo base", tipo="INGRESO")
    return Movimiento.objects.create(
        usuario=usuario, tipo="INGRESO", categoria=cat, monto=Decimal("1000000"),
        fecha_registro=timezone.now() - timedelta(days=60),
    )


def _ejecutar(client, prog, accion="aceptar"):
    return client.post(f"/api/programaciones/{prog.pk}/ejecutar/", {"accion": accion},
                       content_type="application/json")


class TestVistaWeb:
    @pytest.mark.django_db
    def test_requiere_login(self):
        r = Client().get("/programaciones/")
        assert r.status_code == 302
        assert "login" in r.url

    @pytest.mark.django_db
    def test_autenticado_ve_pagina(self, client_auto):
        assert client_auto.get("/programaciones/").status_code == 200


class TestCalendario:
    def test_ocurrencia_mensual_sin_corrimiento(self):
        inicio = date(2026, 1, 31)
        assert ocurrencia(inicio, "MENSUAL", 1) == date(2026, 2, 28)
        assert ocurrencia(inicio, "MENSUAL", 2) == date(2026, 3, 31)

    def test_primera_ocurrencia_desde(self):
        assert primera_ocurrencia_desde(date(2026, 1, 5), "MENSUAL", date(2026, 3, 6)) == date(2026, 4, 5)
        assert primera_ocurrencia_desde(date(2026, 1, 5), "MENSUAL", date(2026, 3, 5)) == date(2026, 3, 5)

    def test_proxima_inicial_pasada_solo_periodo_en_curso(self):
        assert proxima_inicial(date(2026, 1, 5), "MENSUAL", date(2026, 3, 20)) == date(2026, 3, 5)

    def test_proxima_inicial_futura(self):
        assert proxima_inicial(date(2026, 4, 1), "SEMANAL", date(2026, 3, 20)) == date(2026, 4, 1)


class TestMontoMensual:
    def test_factores(self):
        assert monto_mensual_estimado(Decimal("10000"), "DIARIO") == Decimal("300000")
        assert monto_mensual_estimado(Decimal("100000"), "MENSUAL") == Decimal("100000")
        assert monto_mensual_estimado(Decimal("1200000"), "ANUAL") == Decimal("100000")
        assert monto_mensual_estimado(Decimal("50000"), "QUINCENAL") == Decimal("100000")

    @pytest.mark.django_db
    def test_api_expone_monto_mensual(self, client_auto, cat_egreso, usuario):
        Programacion.objects.create(
            monto_programado=Decimal("10000"), tipo="EGRESO", fecha_inicio=date.today(),
            frecuencia="DIARIO", categoria=cat_egreso, usuario=usuario,
        )
        item = client_auto.get("/api/programaciones/").json()[0]
        assert item["monto_mensual"] == 300000
        assert item["frecuencia_label"] == "Diario"


class TestEdicion:
    @pytest.mark.django_db
    def test_cambiar_categoria_sincroniza_tipo(self, client_auto, prog_activa, cat_ingreso):
        r = client_auto.patch(f"/api/programaciones/{prog_activa.pk}/", {"categoria": cat_ingreso.pk},
                              content_type="application/json")
        assert r.status_code == 200, r.json()
        prog_activa.refresh_from_db()
        assert prog_activa.tipo == "INGRESO"

    @pytest.mark.django_db
    def test_crear_en_pasado_no_acumula_atrasos(self, client_auto, cat_egreso):
        inicio = date.today() - relativedelta(months=3)
        r = client_auto.post("/api/programaciones/", {
            "monto_programado": "50000", "categoria": cat_egreso.pk, "frecuencia": "MENSUAL",
            "fecha_inicio": inicio.isoformat(), "activo": True,
        }, content_type="application/json")
        assert r.status_code == 201, r.json()
        prog = Programacion.objects.get(pk=r.json()["id"])
        assert prog.proxima_ejecucion == inicio + relativedelta(months=3)

    @pytest.mark.django_db
    def test_cambiar_frecuencia_recalcula_proxima(self, client_auto, prog_activa):
        r = client_auto.patch(f"/api/programaciones/{prog_activa.pk}/", {"frecuencia": "SEMANAL"},
                              content_type="application/json")
        assert r.status_code == 200, r.json()
        prog_activa.refresh_from_db()
        assert prog_activa.proxima_ejecucion >= date.today()
        assert (prog_activa.proxima_ejecucion - prog_activa.fecha_inicio).days % 7 == 0

    @pytest.mark.django_db
    def test_cambiar_frecuencia_no_repite_hoy_ya_resuelto(self, client_auto, usuario, cat_egreso):
        hoy = date.today()
        prog = Programacion.objects.create(
            monto_programado=Decimal("8000"), tipo="EGRESO", frecuencia="DIARIO",
            fecha_inicio=hoy, proxima_ejecucion=hoy + timedelta(days=1),
            categoria=cat_egreso, usuario=usuario,
        )
        r = client_auto.patch(f"/api/programaciones/{prog.pk}/", {"frecuencia": "SEMANAL"},
                              content_type="application/json")
        assert r.status_code == 200, r.json()
        prog.refresh_from_db()
        assert prog.proxima_ejecucion == hoy + timedelta(days=7)

    @pytest.mark.django_db
    def test_editar_solo_monto_no_mueve_proxima(self, client_auto, prog_activa):
        r = client_auto.patch(f"/api/programaciones/{prog_activa.pk}/", {"monto_programado": "120000"},
                              content_type="application/json")
        assert r.status_code == 200, r.json()
        prog_activa.refresh_from_db()
        assert prog_activa.proxima_ejecucion == date.today()

    @pytest.mark.django_db
    def test_reactivar_omite_periodos_pausados(self, client_auto, prog_activa):
        Programacion.objects.filter(pk=prog_activa.pk).update(
            activo=False, proxima_ejecucion=date.today() - timedelta(days=20))
        r = client_auto.patch(f"/api/programaciones/{prog_activa.pk}/", {"activo": True},
                              content_type="application/json")
        assert r.status_code == 200, r.json()
        prog_activa.refresh_from_db()
        assert prog_activa.proxima_ejecucion >= date.today()

    @pytest.mark.django_db
    def test_no_reactiva_terminada(self, client_auto, prog_activa):
        Programacion.objects.filter(pk=prog_activa.pk).update(
            activo=False, fecha_inicio=date.today() - timedelta(days=90),
            fecha_fin=date.today() - timedelta(days=1))
        r = client_auto.patch(f"/api/programaciones/{prog_activa.pk}/", {"activo": True},
                              content_type="application/json")
        assert r.status_code == 400


class TestEjecucion:
    @pytest.mark.django_db
    def test_movimiento_usa_fecha_programada(self, client_auto, prog_activa, con_saldo):
        fecha = date.today() - timedelta(days=3)
        Programacion.objects.filter(pk=prog_activa.pk).update(proxima_ejecucion=fecha)
        r = _ejecutar(client_auto, prog_activa)
        assert r.status_code == 200, r.json()
        mov = Movimiento.objects.get(pk=r.json()["movimiento"]["id"])
        assert timezone.localtime(mov.fecha_registro).date() == fecha

    @pytest.mark.django_db
    def test_aceptar_con_tipo_desactualizado_usa_categoria(self, client_auto, prog_activa, cat_ingreso):
        Programacion.objects.filter(pk=prog_activa.pk).update(categoria=cat_ingreso, tipo="EGRESO")
        r = _ejecutar(client_auto, prog_activa)
        assert r.status_code == 200, r.json()
        assert r.json()["movimiento"]["tipo"] == "INGRESO"

    @pytest.mark.django_db
    def test_sin_saldo_rechaza_egreso(self, client_auto, prog_activa):
        r = _ejecutar(client_auto, prog_activa)
        assert r.status_code == 400
        assert "disponibilidad" in r.json()["error"]

    @pytest.mark.django_db
    def test_un_solo_registro_de_historial_por_movimiento(self, client_auto, prog_activa, con_saldo):
        from historial.models import AccionHistorial
        r = _ejecutar(client_auto, prog_activa)
        mov_id = str(r.json()["movimiento"]["id"])
        assert AccionHistorial.objects.filter(
            referencia_id=mov_id, modulo=AccionHistorial.ModuloChoices.EGRESOS).count() == 1

    @pytest.mark.django_db
    def test_avanza_desde_fecha_inicio(self, client_auto, usuario, cat_egreso, con_saldo):
        prog = Programacion.objects.create(
            monto_programado=Decimal("1000"), tipo="EGRESO", frecuencia="MENSUAL",
            fecha_inicio=date(2026, 1, 31), proxima_ejecucion=date(2026, 2, 28),
            categoria=cat_egreso, usuario=usuario,
        )
        r = _ejecutar(client_auto, prog, "rechazar")
        assert r.status_code == 200, r.json()
        prog.refresh_from_db()
        assert prog.proxima_ejecucion == date(2026, 3, 31)

    @pytest.mark.django_db
    def test_pendientes_ordenados_por_fecha(self, usuario, cat_egreso):
        for dias in (2, 10, 5):
            Programacion.objects.create(
                monto_programado=Decimal("1000"), tipo="EGRESO", frecuencia="MENSUAL",
                fecha_inicio=date.today() - timedelta(days=dias),
                proxima_ejecucion=date.today() - timedelta(days=dias),
                categoria=cat_egreso, usuario=usuario,
            )
        fechas = [p["fecha_pendiente"] for p in obtener_pendientes(usuario)]
        assert fechas == sorted(fechas)
        assert len(fechas) == 3
