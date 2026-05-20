import pytest
import json
from decimal import Decimal
from datetime import date, timedelta, datetime
from unittest.mock import patch, MagicMock
from django.test import Client
from django.utils import timezone

from usuarios.models import Usuario
from categorias.models import Categoria
from movimientos.models import Movimiento
from dashboard.models import ResumenMensual
from ahorros.models import AhorroMeta, AporteAhorro
from presupuesto.models import Presupuesto
from programaciones.models import Programacion
from agente_financiero.models import MensajeChat, AlertaDiaria
from agente_financiero.recolector import RecolectorDatos
from agente_financiero.prompt_builder import construir_prompt
from agente_financiero.herramientas import EjecutorHerramientas
from agente_financiero.alertas_service import (
    _detectar_situaciones,
    _alertas_fallback,
    _construir_prompt_alertas,
    generar_alertas,
)


pytestmark = pytest.mark.django_db


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
def cat_ahorro():
    return Categoria.objects.create(nombre="Viaje", tipo="AHORRO")

@pytest.fixture
def client_auto(usuario):
    c = Client()
    c.force_login(usuario)
    return c


# ── Models ────────────────────────────────────────────────────────────────────

class TestMensajeChat:
    def test_crear_mensaje(self, usuario):
        msg = MensajeChat.objects.create(usuario=usuario, rol="user", contenido="Hola")
        assert msg.rol == "user"
        assert msg.contenido == "Hola"
        assert str(msg).startswith(f"[{usuario.username}]")

    def test_orden_cronologico(self, usuario):
        MensajeChat.objects.create(usuario=usuario, rol="user", contenido="1")
        MensajeChat.objects.create(usuario=usuario, rol="user", contenido="2")
        msgs = MensajeChat.objects.filter(usuario=usuario)
        assert msgs[0].contenido == "1"
        assert msgs[1].contenido == "2"


class TestAlertaDiariaDebeMostrar:
    def test_nunca_mostrada(self, usuario):
        assert AlertaDiaria.debe_mostrar(usuario) is True

    def test_mostrada_hace_poco(self, usuario):
        AlertaDiaria.objects.create(usuario=usuario, alertas_json=[],
            generado_en=timezone.now())
        assert AlertaDiaria.debe_mostrar(usuario) is False

    def test_mostrada_hace_mas_de_6h(self, usuario):
        alerta = AlertaDiaria.objects.create(usuario=usuario, alertas_json=[])
        AlertaDiaria.objects.filter(pk=alerta.pk).update(
            generado_en=timezone.now() - timedelta(hours=7))
        assert AlertaDiaria.debe_mostrar(usuario) is True

    def test_mostrada_dia_anterior(self, usuario):
        alerta = AlertaDiaria.objects.create(usuario=usuario, alertas_json=[])
        AlertaDiaria.objects.filter(pk=alerta.pk).update(
            generado_en=timezone.now() - timedelta(days=1))
        assert AlertaDiaria.debe_mostrar(usuario) is True


# ── RecolectorDatos ───────────────────────────────────────────────────────────

class TestRecolectorDatos:
    def test_recolectar_sin_datos(self, usuario):
        r = RecolectorDatos(usuario).recolectar_todo()
        assert r["usuario"]["nombre"] == "testuser"
        assert r["usuario"]["email"] == "test@example.com"
        assert r["resumen_mensual"]["total_ingresos"] == 0
        assert r["metas_ahorro"] == []
        assert r["presupuestos"] == []
        assert r["programaciones"] == []
        assert "mes" in r
        assert "anio" in r

    def test_recolectar_con_resumen(self, usuario):
        ResumenMensual.objects.create(usuario=usuario, mes=date.today().month,
            anio=date.today().year, total_ingresos=Decimal("1000000"),
            total_egresos=Decimal("400000"), disponible=Decimal("600000"))
        r = RecolectorDatos(usuario).recolectar_todo()
        assert r["resumen_mensual"]["total_ingresos"] == 1000000.0
        assert r["resumen_mensual"]["disponible"] == 600000.0

    def test_recolectar_con_movimientos(self, usuario, cat_egreso, cat_ingreso):
        Movimiento.objects.create(usuario=usuario, categoria=cat_ingreso, tipo="INGRESO", monto=Decimal("500000"))
        Movimiento.objects.create(usuario=usuario, categoria=cat_egreso, tipo="EGRESO", monto=Decimal("100000"))
        r = RecolectorDatos(usuario).recolectar_todo()
        assert r["resumen_mensual"]["total_ingresos"] == 500000.0
        assert r["resumen_mensual"]["total_egresos"] == 100000.0
        assert len(r["ultimos_movimientos"]) >= 1

    def test_recolectar_con_presupuesto(self, usuario, cat_egreso):
        Presupuesto.objects.create(limite=Decimal("500000"),
            fecha_inicio=date.today() - timedelta(days=30),
            fecha_fin=date.today() + timedelta(days=30),
            isActivo=True, categoria=cat_egreso, usuario=usuario)
        r = RecolectorDatos(usuario).recolectar_todo()
        assert len(r["presupuestos"]) == 1
        assert r["presupuestos"][0]["categoria"] == "Comida"

    def test_recolectar_con_programacion(self, usuario, cat_egreso):
        Programacion.objects.create(monto_programado=Decimal("100000"), tipo="EGRESO",
            fecha_inicio=date.today(), frecuencia="MENSUAL", activo=True,
            categoria=cat_egreso, usuario=usuario)
        r = RecolectorDatos(usuario).recolectar_todo()
        assert len(r["programaciones"]) == 1

    def test_recolectar_con_meta_ahorro(self, usuario, cat_ahorro):
        meta = AhorroMeta.objects.create(monto_meta=Decimal("1000000"),
            total_acumulado=Decimal("200000"), frecuencia="MENSUAL",
            fecha_meta=date.today() + timedelta(days=60), estado="ACTIVO",
            cantidad_cuotas=10, categoria=cat_ahorro, usuario=usuario)
        r = RecolectorDatos(usuario).recolectar_todo()
        assert len(r["metas_ahorro"]) == 1
        assert r["metas_ahorro"][0]["monto_meta"] == 1000000.0


# ── PromptBuilder ─────────────────────────────────────────────────────────────

class TestConstruirPrompt:
    def test_estructura_basica(self, usuario):
        datos = {
            "usuario": {"nombre": "testuser"},
            "resumen_mensual": {"total_ingresos": 0, "total_egresos": 0, "disponible": 0, "total_ahorrado": 0},
            "metas_ahorro": [],
            "presupuestos": [],
            "programaciones": [],
            "mes": date.today().month,
            "anio": date.today().year,
            "ultimos_movimientos": [],
        }
        msgs = construir_prompt(datos, "¿Cómo van mis finanzas?")
        assert len(msgs) >= 2
        assert msgs[0]["role"] == "system"
        assert msgs[-1]["role"] == "user"
        assert msgs[-1]["content"] == "¿Cómo van mis finanzas?"

    def test_con_historial(self, usuario):
        datos = {"usuario": {"nombre": "testuser"},
            "resumen_mensual": {"total_ingresos": 0, "total_egresos": 0, "disponible": 0, "total_ahorrado": 0},
            "metas_ahorro": [], "presupuestos": [], "programaciones": [],
            "mes": date.today().month, "anio": date.today().year, "ultimos_movimientos": []}
        historial = [
            type("Msg", (), {"rol": "user", "contenido": "Hola"})(),
            type("Msg", (), {"rol": "bot", "contenido": "¡Hola! ¿En qué puedo ayudarte?"})(),
        ]
        msgs = construir_prompt(datos, "Dame un resumen", historial)
        assert len(msgs) == 4
        assert msgs[1]["content"] == "Hola"


# ── EjecutorHerramientas ──────────────────────────────────────────────────────

class TestEjecutorHerramientas:
    def test_herramienta_no_reconocida(self, usuario):
        e = EjecutorHerramientas(usuario)
        res = json.loads(e.ejecutar("herramienta_inexistente", {}))
        assert "error" in res

    def test_obtener_movimientos_sin_filtros(self, usuario, cat_egreso, cat_ingreso):
        Movimiento.objects.create(usuario=usuario, categoria=cat_ingreso, tipo="INGRESO", monto=Decimal("500000"))
        Movimiento.objects.create(usuario=usuario, categoria=cat_egreso, tipo="EGRESO", monto=Decimal("100000"))
        e = EjecutorHerramientas(usuario)
        res = json.loads(e.ejecutar("obtener_movimientos", {}))
        assert res["total_registros"] == 2
        assert len(res["movimientos"]) == 2

    def test_obtener_movimientos_filtro_tipo(self, usuario, cat_egreso, cat_ingreso):
        Movimiento.objects.create(usuario=usuario, categoria=cat_ingreso, tipo="INGRESO", monto=Decimal("500000"))
        Movimiento.objects.create(usuario=usuario, categoria=cat_egreso, tipo="EGRESO", monto=Decimal("100000"))
        e = EjecutorHerramientas(usuario)
        res = json.loads(e.ejecutar("obtener_movimientos", {"tipo": "EGRESO"}))
        assert res["total_registros"] == 1
        assert res["movimientos"][0]["tipo"] == "EGRESO"

    def test_obtener_movimientos_sin_resultados(self, usuario):
        e = EjecutorHerramientas(usuario)
        res = json.loads(e.ejecutar("obtener_movimientos", {"tipo": "EGRESO"}))
        assert res["total_registros"] == 0

    def test_obtener_resumen_periodo(self, usuario, cat_egreso, cat_ingreso):
        hoy = date.today()
        Movimiento.objects.create(usuario=usuario, categoria=cat_ingreso, tipo="INGRESO",
            monto=Decimal("1000000"), fecha_registro=timezone.now())
        Movimiento.objects.create(usuario=usuario, categoria=cat_egreso, tipo="EGRESO",
            monto=Decimal("300000"), fecha_registro=timezone.now())
        e = EjecutorHerramientas(usuario)
        res = json.loads(e.ejecutar("obtener_resumen_periodo", {"mes": hoy.month, "anio": hoy.year}))
        assert res["total_ingresos"] == 1000000.0
        assert res["total_egresos"] == 300000.0
        assert res["balance"] == 700000.0

    def test_obtener_gastos_por_categoria(self, usuario, cat_egreso):
        cat2 = Categoria.objects.create(nombre="Transporte", tipo="EGRESO")
        Movimiento.objects.create(usuario=usuario, categoria=cat_egreso, tipo="EGRESO",
            monto=Decimal("200000"), fecha_registro=timezone.now())
        Movimiento.objects.create(usuario=usuario, categoria=cat2, tipo="EGRESO",
            monto=Decimal("100000"), fecha_registro=timezone.now())
        e = EjecutorHerramientas(usuario)
        res = json.loads(e.ejecutar("obtener_gastos_por_categoria", {"anio": date.today().year}))
        assert res["total_egresos"] == 300000.0
        assert len(res["desglose_por_categoria"]) == 2


# ── AlertasService ────────────────────────────────────────────────────────────

class TestDetectarSituaciones:
    def test_balance_negativo(self):
        datos = {"resumen_mensual": {"disponible": -50000, "total_ingresos": 100000, "total_egresos": 150000, "total_ahorrado": 0},
                 "presupuestos": [], "metas_ahorro": []}
        sit = _detectar_situaciones(datos)
        assert any("NEGATIVO" in s["hecho"] for s in sit)

    def test_presupuesto_agotado(self):
        datos = {"resumen_mensual": {"disponible": 500000, "total_ingresos": 1000000, "total_egresos": 500000, "total_ahorrado": 0},
                 "presupuestos": [{"categoria": "Comida", "gastado": 500000, "limite": 500000, "porcentaje_usado": 100, "disponible": 0}],
                 "metas_ahorro": []}
        sit = _detectar_situaciones(datos)
        assert any("AGOTADO" in s["hecho"] for s in sit)

    def test_presupuesto_en_alerta(self):
        datos = {"resumen_mensual": {"disponible": 500000, "total_ingresos": 1000000, "total_egresos": 500000, "total_ahorrado": 0},
                 "presupuestos": [{"categoria": "Comida", "gastado": 400000, "limite": 500000, "porcentaje_usado": 80, "disponible": 100000}],
                 "metas_ahorro": []}
        sit = _detectar_situaciones(datos)
        assert any("80%" in s["hecho"] for s in sit)

    def test_sin_situaciones_logro(self):
        datos = {"resumen_mensual": {"disponible": 300000, "total_ingresos": 1000000, "total_egresos": 700000, "total_ahorrado": 100000},
                 "presupuestos": [], "metas_ahorro": [{"porcentaje": 50}]}
        sit = _detectar_situaciones(datos)
        assert any("van bien" in s["hecho"] for s in sit)

    def test_cuotas_pendientes(self):
        datos = {"resumen_mensual": {"disponible": 300000, "total_ingresos": 1000000, "total_egresos": 700000, "total_ahorrado": 0},
                 "presupuestos": [], "metas_ahorro": [{"cuotas_pendientes": 3, "porcentaje": 50}]}
        sit = _detectar_situaciones(datos)
        assert any("cuota" in s["hecho"] for s in sit)


class TestAlertasFallback:
    def test_estructura(self):
        sit = [{"tipo_sugerido": "critica", "hecho": "Algo grave"}, {"tipo_sugerido": "info", "hecho": "Algo menor"}]
        alertas = _alertas_fallback(sit)
        assert len(alertas) == 2
        assert alertas[0]["tipo"] == "critica"
        assert alertas[0]["mensaje"] == "Algo grave"
        assert alertas[1]["tipo"] == "info"


class TestGenerarAlertas:
    @patch("agente_financiero.alertas_service.settings.GROQ_API_KEY", None)
    def test_sin_api_key_fallback(self, usuario, cat_egreso):
        Presupuesto.objects.create(limite=Decimal("500000"),
            fecha_inicio=date.today() - timedelta(days=30),
            fecha_fin=date.today() + timedelta(days=30),
            isActivo=True, categoria=cat_egreso, usuario=usuario)
        alertas = generar_alertas(usuario)
        assert isinstance(alertas, list)

    @patch("agente_financiero.alertas_service.requests.post")
    def test_con_api_key(self, mock_post, usuario, cat_egreso):
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": '[{"tipo": "info", "titulo": "Test", "mensaje": "Test msg", "accion": null}]'}}]
        }
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.status_code = 200
        Presupuesto.objects.create(limite=Decimal("500000"),
            fecha_inicio=date.today() - timedelta(days=30),
            fecha_fin=date.today() + timedelta(days=30),
            isActivo=True, categoria=cat_egreso, usuario=usuario)
        ResumenMensual.objects.create(usuario=usuario,
            mes=date.today().month, anio=date.today().year,
            total_ingresos=Decimal("1000000"), total_egresos=Decimal("0"),
            disponible=Decimal("500000"))
        with patch("agente_financiero.alertas_service.settings.GROQ_API_KEY", "sk-test"):
            alertas = generar_alertas(usuario)
        assert len(alertas) >= 1
        assert alertas[0]["tipo"] == "info"

    @patch("agente_financiero.alertas_service.requests.post")
    def test_fallback_en_error_api(self, mock_post, usuario):
        mock_post.side_effect = Exception("API error")
        with patch("agente_financiero.alertas_service.settings.GROQ_API_KEY", "sk-test"):
            alertas = generar_alertas(usuario)
        assert isinstance(alertas, list)


# ── API Chat ──────────────────────────────────────────────────────────────────

class TestChatAPI:
    @pytest.mark.django_db
    def test_get_historial_vacio(self, client_auto):
        r = client_auto.get("/api/agente/chat/")
        assert r.status_code == 200
        assert r.json()["mensajes"] == []

    @pytest.mark.django_db
    def test_get_historial_con_mensajes(self, client_auto, usuario):
        MensajeChat.objects.create(usuario=usuario, rol="user", contenido="Hola")
        MensajeChat.objects.create(usuario=usuario, rol="bot", contenido="¡Hola!")
        r = client_auto.get("/api/agente/chat/")
        assert len(r.json()["mensajes"]) == 2

    @pytest.mark.django_db
    def test_post_mensaje_vacio(self, client_auto):
        r = client_auto.post("/api/agente/chat/", {"mensaje": ""}, content_type="application/json")
        assert r.status_code == 400

    @patch("agente_financiero.api_views.preguntar_a_groq")
    @pytest.mark.django_db
    def test_post_mensaje_valido(self, mock_groq, client_auto):
        mock_groq.return_value = "Respuesta de prueba"
        r = client_auto.post("/api/agente/chat/", {"mensaje": "Hola"},
                             content_type="application/json")
        assert r.status_code == 200, r.json()
        assert r.json()["respuesta"] == "Respuesta de prueba"
        assert r.json()["ok"] is True

    @pytest.mark.django_db
    def test_mensaje_demasiado_largo(self, client_auto):
        r = client_auto.post("/api/agente/chat/", {"mensaje": "a" * 1001},
                             content_type="application/json")
        assert r.status_code == 400

    @pytest.mark.django_db
    def test_no_autenticado_chat(self):
        r = Client().post("/api/agente/chat/", {"mensaje": "Hola"},
                          content_type="application/json")
        assert r.status_code in (302, 401)

    @pytest.mark.django_db
    def test_limpiar_chat(self, client_auto, usuario):
        MensajeChat.objects.create(usuario=usuario, rol="user", contenido="Hola")
        r = client_auto.post("/api/agente/limpiar/")
        assert r.status_code == 200
        assert r.json()["eliminados"] == 1


# ── API Alertas ───────────────────────────────────────────────────────────────

class TestAlertasAPI:
    @pytest.mark.django_db
    def test_get_alertas_sin_datos(self, client_auto):
        r = client_auto.get("/api/agente/alertas/")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

    @pytest.mark.django_db
    def test_get_alertas_con_vigente(self, client_auto, usuario):
        AlertaDiaria.objects.create(usuario=usuario, alertas_json=[{"test": "data"}],
            generado_en=timezone.now())
        r = client_auto.get("/api/agente/alertas/")
        assert r.status_code == 200
        assert len(r.json()["alertas"]) > 0

    @pytest.mark.django_db
    def test_post_marcar_vistas(self, client_auto, usuario):
        alerta = AlertaDiaria.objects.create(usuario=usuario, alertas_json=[{"test": "data"}])
        r = client_auto.post("/api/agente/alertas/", {"registro_id": alerta.id},
                             content_type="application/json")
        assert r.status_code == 200
        assert r.json()["ok"] is True
        alerta.refresh_from_db()
        assert alerta.visto_en is not None

    @pytest.mark.django_db
    def test_no_autenticado_alertas(self):
        r = Client().get("/api/agente/alertas/")
        assert r.status_code == 401
