"""Tests de regresion de la auditoria de seguridad (Fase 1)."""
import base64
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import timezone

from gastu_django.exportacion import texto_seguro
from gastu_django.pdf_seguro import imagen_png_segura, link_callback_seguro
from gastu_django.ratelimit_keys import ip_cliente

PNG_1X1 = 'data:image/png;base64,' + base64.b64encode(
    b'\x89PNG\r\n\x1a\n' + b'\x00' * 32
).decode()


@pytest.fixture
def usuario(db):
    return get_user_model().objects.create_user(username='luis', email='luis@ejemplo.com', password='Clave123!x')


@pytest.fixture
def cliente(usuario):
    c = Client()
    c.force_login(usuario)
    return c


# ── PDF: SSRF ────────────────────────────────────────────────────

@pytest.mark.parametrize('valor', [
    'http://169.254.169.254/latest/meta-data/',
    'file:///etc/passwd',
    'C:/Windows/win.ini',
    'data:image/svg+xml;base64,PHN2Zz4=',
    'data:image/png;base64,' + base64.b64encode(b'no es png').decode(),
])
def test_imagen_png_segura_rechaza_urls_y_no_png(valor):
    assert imagen_png_segura(valor) == ''


def test_imagen_png_segura_acepta_png():
    assert imagen_png_segura(PNG_1X1) == PNG_1X1


@pytest.mark.parametrize('uri', ['http://redis:6379/', '//evil/x', 'file:///etc/passwd', 'manage.py'])
def test_link_callback_bloquea_recursos_externos_y_locales(uri):
    assert link_callback_seguro(uri) == 'data:,'


def test_pdf_dashboard_no_descarga_urls(cliente):
    # En equipos con Control de aplicaciones de Windows la DLL de python-bidi puede estar bloqueada.
    pytest.importorskip('xhtml2pdf.pisa', exc_type=ImportError)
    with patch('urllib.request.urlopen') as urlopen, patch('requests.get') as get:
        resp = cliente.post(reverse('dashboard:exportar_pdf'), {
            'img_pie': 'http://169.254.169.254/latest/meta-data/',
            'img_tendencia': 'file:///etc/passwd',
        })
    assert resp.status_code == 200
    urlopen.assert_not_called()
    get.assert_not_called()


# ── Panel admin: escalada ───────────────────────────────────────

def test_admin_no_puede_cambiar_password_del_superusuario(db):
    User = get_user_model()
    root = User.objects.create_superuser(username='root', email='root@ejemplo.com', password='Original123!')
    admin = User.objects.create_user(username='adm', email='adm@ejemplo.com', password='Clave123!x', rol='ADMIN')
    c = Client()
    c.force_login(admin)
    resp = c.post(reverse('panel_admin:editar_usuario', args=[root.pk]), {
        'username': 'root', 'email': 'root@ejemplo.com', 'password': 'Hackeado123!',
    })
    assert resp.status_code == 403
    root.refresh_from_db()
    assert root.check_password('Original123!')


def test_admin_si_puede_editar_usuario_normal(db, usuario):
    admin = get_user_model().objects.create_user(username='adm', email='adm@ejemplo.com', password='Clave123!x', rol='ADMIN')
    c = Client()
    c.force_login(admin)
    resp = c.post(reverse('panel_admin:editar_usuario', args=[usuario.pk]), {
        'username': 'luis2', 'email': 'luis@ejemplo.com',
    })
    assert resp.json()['ok'] is True


# ── Rate limit con la IP real ───────────────────────────────────

def test_ip_cliente_usa_x_real_ip_solo_detras_del_proxy():
    rf = RequestFactory()
    detras = rf.get('/', REMOTE_ADDR='172.18.0.5', HTTP_X_REAL_IP='200.1.2.3')
    directo = rf.get('/', REMOTE_ADDR='200.9.9.9', HTTP_X_REAL_IP='1.1.1.1')
    basura = rf.get('/', REMOTE_ADDR='172.18.0.5', HTTP_X_REAL_IP='no-es-ip')
    assert ip_cliente(detras) == '200.1.2.3'
    assert ip_cliente(directo) == '200.9.9.9'
    assert ip_cliente(basura) == '172.18.0.5'


def test_login_bloqueado_por_ip_no_afecta_a_otro_cliente(db, usuario):
    cache.clear()
    atacante = Client(REMOTE_ADDR='172.18.0.5', HTTP_X_REAL_IP='200.1.2.3')
    for _ in range(6):
        resp = atacante.post(reverse('login'), {'email': 'x@ejemplo.com', 'password': 'mala'})
    assert resp.status_code == 429
    legitimo = Client(REMOTE_ADDR='172.18.0.5', HTTP_X_REAL_IP='200.4.5.6')
    resp = legitimo.post(reverse('login'), {'email': 'luis@ejemplo.com', 'password': 'Clave123!x'})
    assert resp.status_code == 302
    cache.clear()


def test_ver_formulario_de_login_no_consume_intentos(db):
    cache.clear()
    c = Client()
    for _ in range(8):
        assert c.get(reverse('login')).status_code == 200
    cache.clear()


# ── Logout solo por POST ────────────────────────────────────────

def test_logout_por_get_no_cierra_sesion(cliente):
    cliente.get(reverse('logout'))
    assert cliente.get(reverse('dashboard:home')).status_code == 200


def test_logout_por_post_cierra_sesion(cliente):
    cliente.post(reverse('logout'))
    resp = cliente.get(reverse('dashboard:home'))
    assert resp.status_code == 302


# ── Exportaciones: inyeccion de formulas ────────────────────────

@pytest.mark.parametrize('valor', ['=HYPERLINK("http://evil")', '+1+1', '-2+3', '@SUM(A1)', '\t=1'])
def test_texto_seguro_neutraliza_formulas(valor):
    assert texto_seguro(valor).startswith("'")


def test_texto_seguro_no_toca_numeros_ni_texto_normal():
    assert texto_seguro(-5000) == -5000
    assert texto_seguro('Almuerzo') == 'Almuerzo'


# ── Ahorros: topes de cuotas ────────────────────────────────────

def test_meta_diaria_a_muy_largo_plazo_se_rechaza(db):
    from ahorros.forms import AhorroMetaForm
    from categorias.models import Categoria
    cat = Categoria.objects.create(nombre='Viaje', tipo='AHORRO')
    form = AhorroMetaForm(data={
        'categoria': cat.pk, 'monto_meta': '1000000', 'frecuencia': 'DIARIA',
        'fecha_meta': (timezone.localdate() + timedelta(days=365 * 9)).isoformat(),
        'descripcion': 'x',
    })
    assert not form.is_valid()


def test_meta_con_millones_de_cuotas_se_rechaza(db):
    from ahorros.forms import AhorroMetaForm
    from categorias.models import Categoria
    cat = Categoria.objects.create(nombre='Casa', tipo='AHORRO')
    form = AhorroMetaForm(data={
        'categoria': cat.pk, 'monto_meta': '1000000', 'frecuencia': 'MENSUAL',
        'cantidad_cuotas': '2000000', 'descripcion': 'x',
    })
    assert not form.is_valid()


def test_calcular_campo_faltante_tiene_tope():
    from datetime import date
    from ahorros.services import MAX_CUOTAS, calcular_campo_faltante
    _, cuotas = calcular_campo_faltante(date(9999, 1, 1), None, 'DIARIA', fecha_base=date(2026, 1, 1))
    assert cuotas <= MAX_CUOTAS + 1


# ── Cabeceras y plantillas ──────────────────────────────────────

def test_respuesta_lleva_csp(cliente):
    resp = cliente.get(reverse('dashboard:home'))
    assert "object-src 'none'" in resp.get('Content-Security-Policy-Report-Only', '')


def test_pie_del_dashboard_usa_json_script(cliente):
    html = cliente.get(reverse('dashboard:home')).content.decode()
    assert 'id="data-pie" type="application/json"' in html
