"""Tests de edición, reactivación, ritmo de gasto y renovación de presupuestos."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.utils import timezone

from categorias.models import Categoria
from movimientos.models import Movimiento
from presupuesto.models import Presupuesto
from presupuesto.serializer import PresupuestoSerializer
from presupuesto.services import (
    RenovacionError,
    obtener_estado_presupuesto,
    periodo_siguiente,
    renovar_presupuesto,
    ritmo_presupuesto,
)
from usuarios.models import Usuario


@pytest.fixture
def usuario():
    return Usuario.objects.create_user(email="presup@example.com", password="pass1234", username="presup")


@pytest.fixture
def cat_egreso():
    return Categoria.objects.create(nombre="Mercado prueba", tipo="EGRESO")


@pytest.fixture
def cat_ingreso():
    return Categoria.objects.create(nombre="Sueldo prueba", tipo="INGRESO")


@pytest.fixture
def client_auto(usuario):
    c = Client()
    c.force_login(usuario)
    return c


@pytest.fixture
def vigente(usuario, cat_egreso):
    return Presupuesto.objects.create(
        limite=Decimal("500000"), fecha_inicio=date.today() - timedelta(days=30),
        fecha_fin=date.today() + timedelta(days=30), is_activo=True, categoria=cat_egreso, usuario=usuario,
    )


@pytest.fixture
def vencido(usuario, cat_egreso):
    return Presupuesto.objects.create(
        limite=Decimal("300000"), fecha_inicio=date.today() - timedelta(days=29),
        fecha_fin=date.today() - timedelta(days=1), is_activo=False, categoria=cat_egreso, usuario=usuario,
    )


def _ctx(usuario):
    return {"request": type("R", (), {"user": usuario})()}


class TestVistaWeb:
    @pytest.mark.django_db
    def test_requiere_login(self):
        assert Client().get("/presupuesto/").status_code == 302


class TestEdicionYReactivacion:
    @pytest.mark.django_db
    def test_editar_presupuesto_que_termina_hoy(self, client_auto, usuario, cat_egreso):
        p = Presupuesto.objects.create(
            limite=Decimal("1000"), fecha_inicio=date.today() - timedelta(days=10),
            fecha_fin=date.today(), is_activo=True, categoria=cat_egreso, usuario=usuario,
        )
        r = client_auto.patch(f"/api/presupuestos/{p.pk}/", {
            "limite": 2000, "fecha_inicio": p.fecha_inicio.isoformat(), "fecha_fin": p.fecha_fin.isoformat(),
        }, content_type="application/json")
        assert r.status_code == 200, r.json()

    @pytest.mark.django_db
    def test_crear_con_fecha_fin_ayer_falla(self, usuario, cat_egreso):
        data = dict(limite=1000, fecha_inicio=(date.today() - timedelta(days=10)).isoformat(),
                    fecha_fin=(date.today() - timedelta(days=1)).isoformat(),
                    is_activo=True, categoria=cat_egreso.id)
        s = PresupuestoSerializer(data=data, context=_ctx(usuario))
        assert not s.is_valid()
        assert "fecha_fin" in s.errors

    @pytest.mark.django_db
    def test_no_reactiva_vencido(self, client_auto, vencido):
        r = client_auto.patch(f"/api/presupuestos/{vencido.pk}/", {"is_activo": True},
                              content_type="application/json")
        assert r.status_code == 400
        assert "Renovar" in str(r.json())

    @pytest.mark.django_db
    def test_rechaza_categoria_de_ingreso(self, usuario, cat_ingreso):
        data = dict(limite=1000, fecha_inicio=date.today().isoformat(),
                    fecha_fin=(date.today() + timedelta(days=30)).isoformat(),
                    is_activo=True, categoria=cat_ingreso.id)
        s = PresupuestoSerializer(data=data, context=_ctx(usuario))
        assert not s.is_valid()
        assert "categoria" in s.errors


class TestRitmo:
    @pytest.mark.django_db
    def test_dias_y_gasto_diario(self, vigente):
        dias, diario = ritmo_presupuesto(vigente, Decimal("310000"))
        assert dias == 31
        assert diario == Decimal("10000")

    @pytest.mark.django_db
    def test_estado_incluye_ritmo(self, vigente):
        e = obtener_estado_presupuesto(vigente)
        assert e["dias_restantes"] == 31
        assert e["gasto_diario"] == round(500000 / 31)

    @pytest.mark.django_db
    def test_excedido_gasto_diario_cero(self, vigente):
        _, diario = ritmo_presupuesto(vigente, Decimal("-5000"))
        assert diario == 0

    @pytest.mark.django_db
    def test_vencido_sin_ritmo(self, vencido):
        assert ritmo_presupuesto(vencido, Decimal("1000")) == (0, None)


class TestPeriodoSiguiente:
    def test_mes_calendario(self):
        assert periodo_siguiente(date(2026, 1, 1), date(2026, 1, 31), hoy=date(2026, 1, 20)) == (
            date(2026, 2, 1), date(2026, 2, 28))

    def test_mes_calendario_renovado_tarde_salta_periodos(self):
        assert periodo_siguiente(date(2026, 1, 1), date(2026, 1, 31), hoy=date(2026, 4, 10)) == (
            date(2026, 4, 1), date(2026, 4, 30))

    def test_periodo_por_dias(self):
        assert periodo_siguiente(date(2026, 1, 10), date(2026, 1, 24), hoy=date(2026, 1, 20)) == (
            date(2026, 1, 25), date(2026, 2, 8))


class TestRenovar:
    @pytest.mark.django_db
    def test_renovar_crea_periodo_vigente(self, vencido):
        nuevo = renovar_presupuesto(vencido)
        assert nuevo.is_activo
        assert nuevo.limite == vencido.limite
        assert nuevo.fecha_inicio <= date.today() <= nuevo.fecha_fin

    @pytest.mark.django_db
    def test_no_renueva_vigente(self, vigente):
        with pytest.raises(RenovacionError):
            renovar_presupuesto(vigente)

    @pytest.mark.django_db
    def test_no_renueva_si_hay_otro_activo(self, vencido, vigente):
        with pytest.raises(RenovacionError):
            renovar_presupuesto(vencido)

    @pytest.mark.django_db
    def test_api_renovar(self, client_auto, vencido):
        r = client_auto.post(f"/api/presupuestos/{vencido.pk}/renovar/")
        assert r.status_code == 201, r.json()
        assert r.json()["data"]["is_activo"] is True

    @pytest.mark.django_db
    def test_api_renovar_ajeno_404(self, vencido):
        otro = Usuario.objects.create_user(email="otro@example.com", password="x", username="otro")
        c = Client()
        c.force_login(otro)
        assert c.post(f"/api/presupuestos/{vencido.pk}/renovar/").status_code == 404

    @pytest.mark.django_db
    def test_con_estado_incluye_inactivos_con_gasto(self, client_auto, vencido, cat_egreso, usuario):
        Movimiento.objects.create(
            usuario=usuario, tipo="EGRESO", categoria=cat_egreso, monto=Decimal("1000"),
            fecha_registro=timezone.now() - timedelta(days=5),
        )
        data = client_auto.get("/api/presupuestos/con_estado/").json()["data"]
        assert data[0]["gastado"] == 1000.0
