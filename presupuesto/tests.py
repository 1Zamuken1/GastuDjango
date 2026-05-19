import pytest
from decimal import Decimal
from datetime import date, timedelta, datetime
from django.test import Client
from django.utils import timezone

from usuarios.models import Usuario
from categorias.models import Categoria
from movimientos.models import Movimiento
from presupuesto.models import Presupuesto
from presupuesto.services import (
    desactivar_presupuestos_vencidos,
    calcular_alerta_presupuesto,
    nivel_alerta,
    obtener_estado_presupuesto,
)
from presupuesto.serializer import PresupuestoSerializer


@pytest.fixture
def usuario():
    return Usuario.objects.create_user(email="test@example.com", password="pass1234", username="testuser")

@pytest.fixture
def cat_egreso():
    return Categoria.objects.create(nombre="Comida", tipo="EGRESO")

@pytest.fixture
def cat_ingreso():
    return Categoria.objects.create(nombre="Salario", tipo="INGRESO")

@pytest.fixture
def presupuesto_valido(usuario, cat_egreso):
    return Presupuesto.objects.create(
        limite=Decimal("500000"),
        fecha_inicio=date.today() - timedelta(days=30),
        fecha_fin=date.today() + timedelta(days=30),
        isActivo=True,
        categoria=cat_egreso,
        usuario=usuario,
    )

@pytest.fixture
def client_auto(usuario):
    c = Client()
    c.force_login(usuario)
    return c


class TestNivelAlerta:
    def test_critica(self):
        assert nivel_alerta(100) == "critica"
        assert nivel_alerta(150) == "critica"

    def test_niveles_escalonados(self):
        assert nivel_alerta(95) == "nivel_95"
        assert nivel_alerta(90) == "nivel_90"
        assert nivel_alerta(85) == "nivel_85"
        assert nivel_alerta(80) == "nivel_80"
        assert nivel_alerta(75) == "nivel_75"
        assert nivel_alerta(70) == "nivel_70"
        assert nivel_alerta(65) == "nivel_65"
        assert nivel_alerta(60) == "nivel_60"
        assert nivel_alerta(55) == "nivel_55"
        assert nivel_alerta(50) == "nivel_50"

    def test_baja(self):
        assert nivel_alerta(0) == "baja"
        assert nivel_alerta(30) == "baja"
        assert nivel_alerta(49) == "baja"


class TestCalcularAlertaPresupuesto:
    @pytest.mark.django_db
    def test_sin_gastos(self, presupuesto_valido):
        total, pct = calcular_alerta_presupuesto(presupuesto_valido)
        assert total == Decimal("0")
        assert pct == 0

    @pytest.mark.django_db
    def test_con_gastos_en_rango(self, presupuesto_valido, cat_egreso, usuario):
        Movimiento.objects.create(usuario=usuario, categoria=cat_egreso, tipo="EGRESO", monto=Decimal("100000"))
        Movimiento.objects.create(usuario=usuario, categoria=cat_egreso, tipo="EGRESO", monto=Decimal("50000"))
        total, pct = calcular_alerta_presupuesto(presupuesto_valido)
        assert total == Decimal("150000")
        assert pct == 30.0

    @pytest.mark.django_db
    def test_solo_egresos_contados(self, presupuesto_valido, cat_egreso, cat_ingreso, usuario):
        Movimiento.objects.create(usuario=usuario, categoria=cat_ingreso, tipo="INGRESO", monto=Decimal("999999"))
        total, pct = calcular_alerta_presupuesto(presupuesto_valido)
        assert total == Decimal("0")


class TestDesactivarPresupuestosVencidos:
    @pytest.mark.django_db
    def test_desactiva_vencidos(self, usuario, cat_egreso):
        p = Presupuesto.objects.create(
            limite=Decimal("100000"),
            fecha_inicio=date.today() - timedelta(days=60),
            fecha_fin=date.today() - timedelta(days=1),
            isActivo=True, categoria=cat_egreso, usuario=usuario,
        )
        res = desactivar_presupuestos_vencidos(usuario)
        p.refresh_from_db()
        assert p.isActivo is False
        assert len(res) == 1
        assert res[0]["id"] == p.id

    @pytest.mark.django_db
    def test_ignora_no_vencidos(self, usuario, cat_egreso, presupuesto_valido):
        res = desactivar_presupuestos_vencidos(usuario)
        assert len(res) == 0

    @pytest.mark.django_db
    def test_sin_presupuestos(self, usuario):
        res = desactivar_presupuestos_vencidos(usuario)
        assert res == []


class TestObtenerEstadoPresupuesto:
    @pytest.mark.django_db
    def test_estructura(self, presupuesto_valido):
        e = obtener_estado_presupuesto(presupuesto_valido)
        assert e["categoria"] == "Comida"
        assert e["limite"] == 500000.0
        assert e["gastado"] == 0.0
        assert "alerta" in e
        assert "porcentaje" in e
        assert "categoria_id" in e


class TestPresupuestoSerializer:
    @pytest.mark.django_db
    def test_valido(self, usuario, cat_egreso):
        data = dict(limite=500000, fecha_inicio=date.today().isoformat(),
                    fecha_fin=(date.today() + timedelta(days=30)).isoformat(),
                    isActivo=True, categoria=cat_egreso.id)
        ctx = {"request": type("R", (), {"user": usuario})()}
        s = PresupuestoSerializer(data=data, context=ctx)
        assert s.is_valid(), s.errors

    @pytest.mark.django_db
    def test_limite_invalido(self, usuario, cat_egreso):
        data = dict(limite=0, fecha_inicio=date.today().isoformat(),
                    fecha_fin=(date.today() + timedelta(days=30)).isoformat(),
                    isActivo=True, categoria=cat_egreso.id)
        ctx = {"request": type("R", (), {"user": usuario})()}
        s = PresupuestoSerializer(data=data, context=ctx)
        assert not s.is_valid()
        assert "limite" in s.errors

    @pytest.mark.django_db
    def test_fecha_fin_pasada(self, usuario, cat_egreso):
        data = dict(limite=500000, fecha_inicio=date.today().isoformat(),
                    fecha_fin=date.today().isoformat(),
                    isActivo=True, categoria=cat_egreso.id)
        ctx = {"request": type("R", (), {"user": usuario})()}
        s = PresupuestoSerializer(data=data, context=ctx)
        assert not s.is_valid()

    @pytest.mark.django_db
    def test_fecha_fin_menor_inicio(self, usuario, cat_egreso):
        data = dict(limite=500000, fecha_inicio=(date.today() + timedelta(days=30)).isoformat(),
                    fecha_fin=(date.today() + timedelta(days=10)).isoformat(),
                    isActivo=True, categoria=cat_egreso.id)
        ctx = {"request": type("R", (), {"user": usuario})()}
        s = PresupuestoSerializer(data=data, context=ctx)
        assert not s.is_valid()

    @pytest.mark.django_db
    def test_categoria_duplicada(self, usuario, cat_egreso, presupuesto_valido):
        data = dict(limite=300000, fecha_inicio=date.today().isoformat(),
                    fecha_fin=(date.today() + timedelta(days=30)).isoformat(),
                    isActivo=True, categoria=cat_egreso.id)
        ctx = {"request": type("R", (), {"user": usuario})()}
        s = PresupuestoSerializer(data=data, context=ctx)
        assert not s.is_valid()


class TestPresupuestoAPI:
    @pytest.mark.django_db
    def test_listar(self, client_auto, presupuesto_valido):
        r = client_auto.get("/api/presupuestos/")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    @pytest.mark.django_db
    def test_crear(self, client_auto, cat_egreso):
        r = client_auto.post("/api/presupuestos/", {
            "limite": 500000, "fecha_inicio": date.today().isoformat(),
            "fecha_fin": (date.today() + timedelta(days=30)).isoformat(),
            "isActivo": True, "categoria": cat_egreso.id,
        }, content_type="application/json")
        assert r.status_code == 201, r.json()
        assert r.json()["limite"] == "500000.00"

    @pytest.mark.django_db
    def test_alertas(self, client_auto, presupuesto_valido):
        r = client_auto.get("/api/presupuestos/alertas/")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    @pytest.mark.django_db
    def test_verificar_vencidos(self, client_auto, usuario, cat_egreso):
        Presupuesto.objects.create(limite=Decimal("100000"),
            fecha_inicio=date.today() - timedelta(days=60),
            fecha_fin=date.today() - timedelta(days=1),
            isActivo=True, categoria=cat_egreso, usuario=usuario)
        r = client_auto.post("/api/presupuestos/verificar_vencidos/")
        assert r.status_code == 200
        assert len(r.json()["desactivados"]) == 1

    @pytest.mark.django_db
    def test_no_autenticado(self):
        r = Client().get("/api/presupuestos/")
        assert r.status_code in (401, 403)
