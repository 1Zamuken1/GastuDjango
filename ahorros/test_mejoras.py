"""Tests de calendario de cuotas, fecha de aporte, estados y resumen de metas."""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import Client
from django.utils import timezone

from ahorros.models import AhorroMeta, AporteAhorro
from ahorros.services import (
    actualizar_estados_usuario,
    calcular_campo_faltante,
    fecha_cuota,
    generar_cuotas,
    proyectar_fin,
    resumen_meta,
)
from categorias.models import Categoria
from dashboard.services import actualizar_resumen
from dashboard.models import ResumenMensual
from movimientos.models import Movimiento
from usuarios.models import Usuario


@pytest.fixture
def usuario():
    return Usuario.objects.create_user(email="ahorro@example.com", password="pass1234", username="ahorrador")


@pytest.fixture
def cat_ahorro():
    return Categoria.objects.create(nombre="Meta prueba", tipo="AHORRO", activo=True)


@pytest.fixture
def client_auto(usuario):
    c = Client()
    c.force_login(usuario)
    return c


@pytest.fixture
def con_saldo(usuario):
    cat = Categoria.objects.create(nombre="Sueldo ahorro", tipo="INGRESO")
    return Movimiento.objects.create(usuario=usuario, tipo="INGRESO", categoria=cat, monto=Decimal("5000000"),
                                     fecha_registro=timezone.now() - timedelta(days=90))


def crear_meta(usuario, categoria, creada, cuotas=6, frecuencia="MENSUAL", monto="600000"):
    meta = AhorroMeta.objects.create(
        usuario=usuario, categoria=categoria, monto_meta=Decimal(monto), frecuencia=frecuencia,
        fecha_meta=creada + timedelta(days=200), cantidad_cuotas=cuotas,
    )
    AhorroMeta.objects.filter(pk=meta.pk).update(fecha_creacion=creada)
    meta.refresh_from_db()
    generar_cuotas(meta)
    return meta


class TestCalendario:
    def test_cuotas_mensuales_sin_corrimiento(self):
        inicio = date(2026, 1, 31)
        assert fecha_cuota(inicio, "MENSUAL", 1) == date(2026, 2, 28)
        assert fecha_cuota(inicio, "MENSUAL", 2) == date(2026, 3, 31)
        assert fecha_cuota(date(2026, 1, 10), "TRIMESTRAL", 4) == date(2027, 1, 10)

    def test_fecha_meta_es_la_ultima_cuota(self):
        fecha_meta, cuotas = calcular_campo_faltante(None, 6, "MENSUAL", fecha_base=date(2026, 11, 9))
        assert cuotas == 6
        assert fecha_meta == date(2027, 4, 10)

    def test_cuotas_desde_fecha_meta(self):
        _, cuotas = calcular_campo_faltante(date(2027, 4, 10), None, "MENSUAL", fecha_base=date(2026, 11, 9))
        assert cuotas == 6

    @pytest.mark.django_db
    def test_generar_cuotas_coincide_con_fecha_meta(self, usuario, cat_ahorro):
        meta = crear_meta(usuario, cat_ahorro, date(2026, 11, 9))
        fechas = list(meta.aporteahorro_set.order_by('fecha_limite').values_list('fecha_limite', flat=True))
        assert fechas[0] == date(2026, 11, 10)
        assert fechas[-1] == date(2027, 4, 10)
        assert all(f.day == 10 for f in fechas)


class TestFechaAporte:
    @pytest.mark.django_db
    def test_aporte_guarda_fecha_y_cuenta_en_el_mes_del_aporte(self, client_auto, usuario, cat_ahorro, con_saldo):
        hoy = timezone.localdate()
        meta = crear_meta(usuario, cat_ahorro, hoy - timedelta(days=95))
        AporteAhorro.objects.filter(ahorro=meta, fecha_limite__lt=hoy).update(estado_ap='PERDIDO')
        r = client_auto.post(f"/ahorros/{meta.pk}/aporte/", {"aporte": "50000", "extraordinario": "true"})
        assert r.status_code == 200, r.json()
        aporte = AporteAhorro.objects.get(ahorro=meta, es_extraordinario=True)
        assert aporte.fecha_aporte == hoy

        actualizar_resumen(usuario=usuario, mes=hoy.month, anio=hoy.year)
        resumen = ResumenMensual.objects.get(usuario=usuario, mes=hoy.month, anio=hoy.year)
        assert resumen.total_ahorros == Decimal("50000")

    @pytest.mark.django_db
    def test_aporte_no_cuenta_en_el_mes_de_creacion(self, usuario, cat_ahorro):
        creada = date(2026, 1, 15)
        meta = crear_meta(usuario, cat_ahorro, creada)
        cuota = meta.aporteahorro_set.order_by('fecha_limite').first()
        AporteAhorro.objects.filter(pk=cuota.pk).update(estado_ap='APORTADO', aporte=Decimal("100000"),
                                                         fecha_aporte=date(2026, 3, 2))
        actualizar_resumen(usuario=usuario, mes=1, anio=2026)
        actualizar_resumen(usuario=usuario, mes=3, anio=2026)
        assert ResumenMensual.objects.get(usuario=usuario, mes=1, anio=2026).total_ahorros == 0
        assert ResumenMensual.objects.get(usuario=usuario, mes=3, anio=2026).total_ahorros == Decimal("100000")


class TestEstados:
    @pytest.mark.django_db
    def test_listar_marca_cuotas_vencidas(self, client_auto, usuario, cat_ahorro):
        meta = crear_meta(usuario, cat_ahorro, timezone.localdate() - timedelta(days=50))
        assert client_auto.get("/ahorros/").status_code == 200
        perdidas = AporteAhorro.objects.filter(ahorro=meta, estado_ap='PERDIDO').count()
        assert perdidas == 2

    @pytest.mark.django_db
    def test_abandono_con_tres_cuotas_vencidas_seguidas(self, usuario, cat_ahorro):
        meta = crear_meta(usuario, cat_ahorro, timezone.localdate() - timedelta(days=100))
        actualizar_estados_usuario(usuario)
        meta.refresh_from_db()
        assert meta.estado == AhorroMeta.Estado.ABANDONADO.value

    @pytest.mark.django_db
    def test_pagar_cuota_vencida_da_mensaje_claro(self, client_auto, usuario, cat_ahorro, con_saldo):
        meta = crear_meta(usuario, cat_ahorro, timezone.localdate() - timedelta(days=40))
        vencida = meta.aporteahorro_set.order_by('fecha_limite').first()
        r = client_auto.post(f"/ahorros/{meta.pk}/aporte/", {"aporte": "100000", "aporte_id": vencida.pk})
        assert r.status_code == 400
        assert "venció" in r.json()["error"]
        assert "estado=" not in r.json()["error"]

    @pytest.mark.django_db
    def test_monto_invalido_no_rompe(self, client_auto, usuario, cat_ahorro):
        meta = crear_meta(usuario, cat_ahorro, timezone.localdate())
        r = client_auto.post(f"/ahorros/{meta.pk}/aporte/", {"aporte": "cien mil", "extraordinario": "true"})
        assert r.status_code == 400
        assert "números" in r.json()["error"]

    def test_etiqueta_estado(self):
        assert AhorroMeta.Estado.SIN_INICIAR.label == "Sin iniciar"


class TestEliminar:
    @pytest.mark.django_db
    def test_eliminar_recalcula_resumen(self, client_auto, usuario, cat_ahorro):
        hoy = timezone.localdate()
        meta = crear_meta(usuario, cat_ahorro, hoy)
        cuota = meta.aporteahorro_set.first()
        AporteAhorro.objects.filter(pk=cuota.pk).update(estado_ap='APORTADO', aporte=Decimal("100000"), fecha_aporte=hoy)
        actualizar_resumen(usuario=usuario, mes=hoy.month, anio=hoy.year)
        assert ResumenMensual.objects.get(usuario=usuario, mes=hoy.month, anio=hoy.year).total_ahorros == Decimal("100000")

        r = client_auto.post(f"/ahorros/{meta.pk}/eliminar/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        assert r.status_code == 200
        assert ResumenMensual.objects.get(usuario=usuario, mes=hoy.month, anio=hoy.year).total_ahorros == 0


class TestResumen:
    @pytest.mark.django_db
    def test_resumen_meta_nueva(self, usuario, cat_ahorro):
        meta = crear_meta(usuario, cat_ahorro, timezone.localdate())
        r = resumen_meta(meta)
        assert r["estado"] == "por_aportar"
        assert r["pagadas"] == 0 and r["total_cuotas"] == 6
        assert r["porcentaje"] == 0
        assert r["proxima"] is not None and r["proxima_disponible"]

    @pytest.mark.django_db
    def test_resumen_atrasada(self, usuario, cat_ahorro):
        meta = crear_meta(usuario, cat_ahorro, timezone.localdate() - timedelta(days=40))
        actualizar_estados_usuario(usuario)
        meta.refresh_from_db()
        assert resumen_meta(meta)["estado"] == "atrasada"

    @pytest.mark.django_db
    def test_proyeccion(self, usuario, cat_ahorro):
        hoy = date(2026, 11, 9)
        meta = crear_meta(usuario, cat_ahorro, hoy - timedelta(days=30))
        meta.total_acumulado = Decimal("150000")
        assert proyectar_fin(meta, hoy) == hoy + timedelta(days=90)

    @pytest.mark.django_db
    def test_detalle_renderiza(self, client_auto, usuario, cat_ahorro):
        meta = crear_meta(usuario, cat_ahorro, timezone.localdate())
        r = client_auto.get(f"/ahorros/{meta.pk}/aporte/")
        assert r.status_code == 200
        assert "Mensual" in r.content.decode()


class TestDashboard:
    @pytest.mark.django_db
    def test_tendencia_con_aportes(self, client_auto, usuario, cat_ahorro):
        """La tendencia diaria del dashboard agrupa los aportes por fecha_aporte (DateField)."""
        hoy = timezone.localdate()
        meta = crear_meta(usuario, cat_ahorro, hoy)
        cuota = meta.aporteahorro_set.first()
        AporteAhorro.objects.filter(pk=cuota.pk).update(estado_ap='APORTADO', aporte=Decimal("100000"), fecha_aporte=hoy)
        r = client_auto.get(f"/dashboard/tendencia/?mes={hoy.month}&anio={hoy.year}")
        assert r.status_code == 200
        assert sum(r.json()["ahorros"]) == 100000
