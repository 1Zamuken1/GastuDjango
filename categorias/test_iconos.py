"""Tests del icono de categoria: sugerencias, API, panel de administracion y movimientos."""
import datetime
from decimal import Decimal

import pytest
from django.test import Client
from django.utils import timezone

from categorias.iconos import ICONOS_CATEGORIA, icono_sugerido
from categorias.models import Categoria
from movimientos.models import Movimiento
from usuarios.models import Usuario


@pytest.fixture
def usuario():
    return Usuario.objects.create_user(email="iconos@example.com", password="pass1234", username="iconos")


@pytest.fixture
def admin():
    return Usuario.objects.create_user(email="admin-iconos@example.com", password="pass1234",
                                       username="adminiconos", is_staff=True, is_superuser=True)


def cliente(u):
    c = Client()
    c.force_login(u)
    return c


class TestSugerencias:
    def test_categorias_base(self):
        assert icono_sugerido("Transporte") == "bus"
        assert icono_sugerido("  Alimentación ") == "utensils"
        assert icono_sugerido("Fondo de emergencia") == "shield"

    def test_desconocida_usa_etiqueta(self):
        assert icono_sugerido("Mascotas") == "tag"

    def test_sugeridos_estan_en_la_lista(self):
        permitidos = {v for v, _ in ICONOS_CATEGORIA}
        assert all(icono_sugerido(n) in permitidos for n in ("Salario", "Vivienda", "Otros ahorros"))


class TestApi:
    @pytest.mark.django_db
    def test_enriched_incluye_icono(self, usuario):
        Categoria.objects.create(nombre="Gimnasio prueba", tipo="EGRESO", icono="dumbbell")
        data = cliente(usuario).get("/api/categorias/enriched/?tipo=EGRESO").json()
        item = next(c for c in data if c["nombre"] == "Gimnasio prueba")
        assert item["icono"] == "dumbbell"


class TestPanel:
    @pytest.mark.django_db
    def test_crear_con_icono(self, admin):
        r = cliente(admin).post("/admin-panel/categorias/crear/",
                                {"nombre": "Mascotas prueba", "tipo": "EGRESO", "icono": "dog"})
        assert r.json()["ok"], r.json()
        assert Categoria.objects.get(nombre="Mascotas prueba").icono == "dog"

    @pytest.mark.django_db
    def test_icono_invalido_usa_sugerido(self, admin):
        cliente(admin).post("/admin-panel/categorias/crear/",
                            {"nombre": "Transporte", "tipo": "INGRESO", "icono": "no-existe"})
        assert Categoria.objects.get(nombre="Transporte", tipo="INGRESO").icono == "bus"

    @pytest.mark.django_db
    def test_editar_y_detalle(self, admin):
        cat = Categoria.objects.create(nombre="Cafe prueba", tipo="EGRESO")
        c = cliente(admin)
        c.post(f"/admin-panel/categorias/{cat.pk}/editar/", {"nombre": "Cafe prueba", "tipo": "EGRESO", "icono": "coffee"})
        assert c.get(f"/admin-panel/categorias/{cat.pk}/detalle/").json()["icono"] == "coffee"

    @pytest.mark.django_db
    def test_listado_muestra_selector(self, admin):
        r = cliente(admin).get("/admin-panel/categorias/")
        assert r.status_code == 200
        html = r.content.decode()
        assert 'id="crear-cat-iconos"' in html and 'id="editar-cat-iconos"' in html


class TestMovimientos:
    @pytest.fixture
    def egreso_noche(self, usuario):
        """Egreso a las 8 p. m. de Bogota: en UTC ya es el dia siguiente."""
        cat = Categoria.objects.create(nombre="Transporte prueba", tipo="EGRESO", icono="bus")
        local = timezone.make_aware(datetime.datetime(2026, 11, 9, 20, 0))
        return Movimiento.objects.create(usuario=usuario, tipo="EGRESO", categoria=cat,
                                         monto=Decimal("10000"), fecha_registro=local)

    @pytest.mark.django_db
    def test_resumen_trae_icono_y_fecha_local(self, usuario, egreso_noche):
        data = cliente(usuario).get("/resumen/?tipo=EGRESO&mes=all&anio=all").json()
        cat = next(c for c in data["categorias"] if c["nombre"] == "Transporte prueba")
        assert cat["icono"] == "bus"
        assert cat["ultimo_corto"] == "9 nov"

    @pytest.mark.django_db
    def test_registros_con_fecha_local(self, usuario, egreso_noche):
        data = cliente(usuario).get(f"/registros-categoria/?categoria={egreso_noche.categoria_id}").json()
        registro = data["registros"][0]
        assert registro["fecha_raw"] == "2026-11-09"

    @pytest.mark.django_db
    def test_card_muestra_icono(self, usuario, egreso_noche):
        html = cliente(usuario).get("/egresos/?mes=all&anio=all").content.decode()
        assert 'data-icono="bus"' in html


class TestPlanificacion:
    @pytest.mark.django_db
    def test_presupuesto_y_programacion_exponen_icono(self, usuario):
        from presupuesto.models import Presupuesto
        from programaciones.models import Programacion
        cat = Categoria.objects.create(nombre="Gimnasio plan", tipo="EGRESO", icono="dumbbell")
        hoy = timezone.localdate()
        Presupuesto.objects.create(usuario=usuario, categoria=cat, limite=Decimal("100000"),
                                   fecha_inicio=hoy, fecha_fin=hoy + datetime.timedelta(days=20), is_activo=True)
        Programacion.objects.create(usuario=usuario, categoria=cat, tipo="EGRESO", monto_programado=Decimal("5000"),
                                    frecuencia="MENSUAL", fecha_inicio=hoy, proxima_ejecucion=hoy)
        c = cliente(usuario)
        assert c.get("/api/presupuestos/con_estado/").json()["data"][0]["categoria_icono"] == "dumbbell"
        assert c.get("/api/programaciones/").json()[0]["categoria_icono"] == "dumbbell"
        assert c.get("/api/programaciones/pendientes/").json()["pendientes"][0]["categoria_icono"] == "dumbbell"
