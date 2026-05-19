import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import Client
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from usuarios.models import Usuario
from categorias.models import Categoria
from movimientos.models import Movimiento
from dashboard.models import ResumenMensual
from programaciones.models import Programacion, EjecucionProgramacion
from programaciones.serializers import ProgramacionSerializer
from programaciones.api_pendientes import (
    calcular_proxima_fecha,
    desactivar_si_vencida,
    serializar_pendiente,
    DELTA_MAP,
)


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
def prog_activa(usuario, cat_egreso):
    return Programacion.objects.create(
        monto_programado=Decimal("100000"),
        tipo="EGRESO",
        descripcion="Arriendo",
        fecha_inicio=date.today() - timedelta(days=30),
        fecha_fin=date.today() + timedelta(days=30),
        frecuencia="MENSUAL",
        proxima_ejecucion=date.today(),
        activo=True,
        categoria=cat_egreso,
        usuario=usuario,
    )

@pytest.fixture
def client_auto(usuario):
    c = Client()
    c.force_login(usuario)
    return c


class TestProgramacionSerializer:
    @pytest.mark.django_db
    def test_valido(self, usuario, cat_egreso):
        data = dict(monto_programado=100000, fecha_inicio=date.today().isoformat(),
                    fecha_fin=(date.today() + timedelta(days=30)).isoformat(),
                    frecuencia="MENSUAL", activo=True, categoria=cat_egreso.id)
        ctx = {"request": type("R", (), {"user": usuario})()}
        s = ProgramacionSerializer(data=data, context=ctx)
        assert s.is_valid(), s.errors

    @pytest.mark.django_db
    def test_monto_invalido(self, usuario, cat_egreso):
        data = dict(monto_programado=0, fecha_inicio=date.today().isoformat(),
                    fecha_fin=(date.today() + timedelta(days=30)).isoformat(),
                    frecuencia="MENSUAL", activo=True, categoria=cat_egreso.id)
        ctx = {"request": type("R", (), {"user": usuario})()}
        s = ProgramacionSerializer(data=data, context=ctx)
        assert not s.is_valid()
        assert "monto_programado" in s.errors

    @pytest.mark.django_db
    def test_fecha_fin_menor_inicio(self, usuario, cat_egreso):
        data = dict(monto_programado=100000,
                    fecha_inicio=(date.today() + timedelta(days=30)).isoformat(),
                    fecha_fin=(date.today() + timedelta(days=10)).isoformat(),
                    frecuencia="MENSUAL", activo=True, categoria=cat_egreso.id)
        ctx = {"request": type("R", (), {"user": usuario})()}
        s = ProgramacionSerializer(data=data, context=ctx)
        assert not s.is_valid()

    @pytest.mark.django_db
    def test_categoria_nombre_read_only(self, usuario, cat_egreso):
        data = dict(monto_programado=100000, fecha_inicio=date.today().isoformat(),
                    fecha_fin=(date.today() + timedelta(days=30)).isoformat(),
                    frecuencia="MENSUAL", activo=True, categoria=cat_egreso.id)
        ctx = {"request": type("R", (), {"user": usuario})()}
        s = ProgramacionSerializer(data=data, context=ctx)
        assert s.is_valid()
        assert "categoria_nombre" in s.fields
        assert s.fields["categoria_nombre"].read_only is True


class TestCalcularProximaFecha:
    @pytest.mark.django_db
    def test_pendiente_hoy(self, usuario, cat_egreso):
        p = Programacion(activo=True, fecha_inicio=date.today(), frecuencia="DIARIO",
                         proxima_ejecucion=None, usuario=usuario, categoria=cat_egreso)
        f = calcular_proxima_fecha(p, date.today())
        assert f == date.today()

    @pytest.mark.django_db
    def test_pendiente_pasado(self, usuario, cat_egreso):
        p = Programacion(activo=True, fecha_inicio=date.today() - timedelta(days=5),
                         frecuencia="DIARIO", proxima_ejecucion=date.today() - timedelta(days=5),
                         usuario=usuario, categoria=cat_egreso)
        f = calcular_proxima_fecha(p, date.today())
        assert f == date.today() - timedelta(days=5)

    @pytest.mark.django_db
    def test_no_pendiente_futuro(self, usuario, cat_egreso):
        p = Programacion(activo=True, fecha_inicio=date.today(),
                         frecuencia="MENSUAL", proxima_ejecucion=date.today() + timedelta(days=15),
                         usuario=usuario, categoria=cat_egreso)
        f = calcular_proxima_fecha(p, date.today())
        assert f is None

    @pytest.mark.django_db
    def test_inactiva_retorna_none(self, usuario, cat_egreso):
        p = Programacion(activo=False, fecha_inicio=date.today() - timedelta(days=10),
                         frecuencia="DIARIO", usuario=usuario, categoria=cat_egreso)
        f = calcular_proxima_fecha(p, date.today())
        assert f is None

    @pytest.mark.django_db
    def test_fecha_fin_expirada(self, usuario, cat_egreso):
        p = Programacion(activo=True, fecha_inicio=date.today() - timedelta(days=60),
                         fecha_fin=date.today() - timedelta(days=1),
                         frecuencia="MENSUAL", proxima_ejecucion=date.today() - timedelta(days=30),
                         usuario=usuario, categoria=cat_egreso)
        f = calcular_proxima_fecha(p, date.today())
        assert f is None

    def test_frecuencia_invalida(self):
        p = Programacion(activo=True, frecuencia="INVALIDA")
        f = calcular_proxima_fecha(p, date.today())
        assert f is None


class TestDesactivarSiVencida:
    @pytest.mark.django_db
    def test_vencida_por_fecha_fin(self, usuario, cat_egreso):
        p = Programacion.objects.create(activo=True, fecha_inicio=date.today() - timedelta(days=60),
            fecha_fin=date.today() - timedelta(days=1), frecuencia="MENSUAL",
            monto_programado=Decimal("100"), tipo="EGRESO",
            categoria=cat_egreso, usuario=usuario)
        assert desactivar_si_vencida(p, date.today()) is True
        p.refresh_from_db()
        assert p.activo is False

    @pytest.mark.django_db
    def test_no_vencida(self, usuario, cat_egreso):
        p = Programacion.objects.create(activo=True, fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=30), frecuencia="MENSUAL",
            monto_programado=Decimal("100"), tipo="EGRESO",
            categoria=cat_egreso, usuario=usuario)
        assert desactivar_si_vencida(p, date.today()) is False
        assert p.activo is True


class TestSerializarPendiente:
    @pytest.mark.django_db
    def test_estructura(self, prog_activa):
        f = date.today() + timedelta(days=1)
        s = serializar_pendiente(prog_activa, f)
        assert s["id"] == prog_activa.id
        assert s["monto_programado"] == "100000.00" or s["monto_programado"] == "100000"
        assert s["frecuencia"] == "MENSUAL"
        assert s["fecha_pendiente"] == f.isoformat()
        assert s["categoria_nombre"] == "Comida"


class TestProgramacionAPI:
    @pytest.mark.django_db
    def test_listar(self, client_auto, prog_activa):
        r = client_auto.get("/api/programaciones/")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    @pytest.mark.django_db
    def test_crear(self, client_auto, cat_egreso):
        r = client_auto.post("/api/programaciones/", {
            "monto_programado": 200000,
            "fecha_inicio": date.today().isoformat(),
            "fecha_fin": (date.today() + timedelta(days=60)).isoformat(),
            "frecuencia": "MENSUAL", "activo": True, "categoria": cat_egreso.id,
        }, content_type="application/json")
        assert r.status_code == 201, r.json()
        assert r.json()["monto_programado"] == "200000.00"

    @pytest.mark.django_db
    def test_pendientes(self, client_auto, prog_activa):
        r = client_auto.get("/api/programaciones/pendientes/")
        assert r.status_code == 200
        assert "pendientes" in r.json()

    @pytest.mark.django_db
    def test_ejecutar_aceptar(self, client_auto, prog_activa, usuario, cat_egreso):
        ResumenMensual.objects.create(usuario=usuario, mes=date.today().month,
            anio=date.today().year, total_ingresos=Decimal("1000000"),
            total_egresos=Decimal("0"), disponible=Decimal("500000"))
        r = client_auto.post(f"/api/programaciones/{prog_activa.pk}/ejecutar/",
            {"accion": "aceptar"}, content_type="application/json")
        assert r.status_code == 200, r.json()
        assert r.json()["ok"] is True
        assert r.json()["accion"] == "aceptar"
        assert r.json()["movimiento"] is not None

    @pytest.mark.django_db
    def test_ejecutar_rechazar(self, client_auto, prog_activa):
        r = client_auto.post(f"/api/programaciones/{prog_activa.pk}/ejecutar/",
            {"accion": "rechazar"}, content_type="application/json")
        assert r.status_code == 200
        assert r.json()["accion"] == "rechazar"

    @pytest.mark.django_db
    def test_ejecutar_sin_disponible(self, client_auto, prog_activa, usuario):
        ResumenMensual.objects.create(usuario=usuario, mes=date.today().month,
            anio=date.today().year, total_ingresos=Decimal("1000"),
            total_egresos=Decimal("0"), disponible=Decimal("10"))
        r = client_auto.post(f"/api/programaciones/{prog_activa.pk}/ejecutar/",
            {"accion": "aceptar"}, content_type="application/json")
        assert r.status_code == 400
        assert "disponibilidad" in r.json()["error"]

    @pytest.mark.django_db
    def test_ejecutar_accion_invalida(self, client_auto, prog_activa):
        r = client_auto.post(f"/api/programaciones/{prog_activa.pk}/ejecutar/",
            {"accion": "invalida"}, content_type="application/json")
        assert r.status_code == 400

    @pytest.mark.django_db
    def test_historial(self, client_auto, prog_activa, usuario, cat_egreso):
        EjecucionProgramacion.objects.create(programacion=prog_activa, usuario=usuario,
            fecha_ejecutada=date.today(), monto=Decimal("100000"),
            categoria_nombre="Comida", tipo="EGRESO")
        r = client_auto.get("/api/programaciones/historial/")
        assert r.status_code == 200
        assert len(r.json()["ejecuciones"]) == 1

    @pytest.mark.django_db
    def test_no_autenticado(self):
        r = Client().get("/api/programaciones/")
        assert r.status_code in (401, 403)
