"""Tests del rediseno de Ingresos, Egresos, Dashboard y Mi perfil (solo presentacion)."""
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from categorias.models import Categoria
from dashboard.templatetags.dashboard_extras import fecha_corta, separar_banco
from movimientos.models import Movimiento
from presupuesto.models import Presupuesto
from presupuesto.services import estado_presupuesto_por_categoria

pytestmark = pytest.mark.django_db


@pytest.fixture
def usuario():
    return get_user_model().objects.create_user(username='rita', email='rita@ejemplo.com', password='Clave123!x')


@pytest.fixture
def cliente(usuario):
    c = Client()
    c.force_login(usuario)
    return c


@pytest.fixture
def presupuesto_en_alerta(usuario):
    cat = Categoria.objects.get_or_create(nombre='Transporte', tipo='EGRESO')[0]
    hoy = date.today()
    Presupuesto.objects.create(usuario=usuario, categoria=cat, limite=Decimal('100000'),
                               fecha_inicio=date(hoy.year, hoy.month, 1), fecha_fin=date(hoy.year, hoy.month, 28),
                               is_activo=True)
    Movimiento.objects.create(usuario=usuario, categoria=cat, tipo='EGRESO', monto=Decimal('95000'),
                              descripcion='UBER (Bancolombia)')
    return cat


@pytest.mark.parametrize('texto,concepto,banco', [
    ('CLARO COLOMBIA (Bancolombia)', 'CLARO COLOMBIA', 'Bancolombia'),
    ('Almuerzo con amigos', 'Almuerzo con amigos', ''),
    ('', '', ''),
])
def test_separar_banco(texto, concepto, banco):
    assert separar_banco(texto) == {'concepto': concepto, 'banco': banco}


def test_fecha_corta():
    assert fecha_corta('09/11/2026') == '09 nov'
    assert fecha_corta('no es fecha') == 'no es fecha'


def test_estado_presupuesto_por_categoria(usuario, presupuesto_en_alerta):
    estado = estado_presupuesto_por_categoria(usuario)[presupuesto_en_alerta.id]
    assert estado['nivel'] == 'alerta' and round(estado['porcentaje']) == 95


def test_egresos_muestran_medidor_de_presupuesto(cliente, presupuesto_en_alerta):
    html = cliente.get('/egresos/').content.decode()
    assert 'cat-presupuesto--alerta' in html
    assert 'Te quedan $5.000' in html


def test_resumen_json_incluye_presupuesto(cliente, presupuesto_en_alerta):
    from django.urls import reverse
    data = cliente.get(reverse('movimientos:resumen_movimientos'), {'tipo': 'EGRESO'}).json()
    assert data['categorias'][0]['presupuesto']['nivel'] == 'alerta'


def test_resumen_sin_all_en_textos(cliente):
    html = cliente.get('/ingresos/').content.decode()
    assert 'Todas las fechas all' not in html
    assert 'todas las fechas' in html.lower()
    # Hero de color restaurado; el disponible aclara que no incluye el ahorro
    assert 'gastu-hero-card--ingresos' in html
    assert 'No incluye lo que tienes ahorrado' in html


def test_insignia_del_dashboard_avisa_presupuestos_en_alerta(cliente, usuario, presupuesto_en_alerta):
    # Con ingresos de sobra: sin esto aplica antes "Gastos superan ingresos del mes".
    salario = Categoria.objects.get_or_create(nombre='Salario', tipo='INGRESO')[0]
    Movimiento.objects.create(usuario=usuario, categoria=salario, tipo='INGRESO', monto=Decimal('1000000'))
    html = cliente.get('/dashboard/').content.decode()
    assert '1 presupuesto al 80% o más' in html
    assert 'Finanzas en orden' not in html.split('id="status-badge-wrap"')[1][:400]


def test_foto_de_perfil_solo_acepta_google(usuario):
    from allauth.socialaccount.models import SocialAccount
    from usuarios.services import foto_de_perfil
    assert foto_de_perfil(usuario) == ''
    cuenta = SocialAccount.objects.create(user=usuario, provider='google', uid='1',
                                          extra_data={'picture': 'https://evil.com/x.png'})
    assert foto_de_perfil(usuario) == ''
    cuenta.extra_data = {'picture': 'https://lh3.googleusercontent.com/a/foto'}
    cuenta.save()
    assert foto_de_perfil(usuario) == 'https://lh3.googleusercontent.com/a/foto'


def test_perfil_con_tildes(cliente):
    html = cliente.get('/perfil/').content.decode()
    for palabra in ('Cambiar contraseña', 'Teléfono', 'acción permanente', 'Configuración'):
        assert palabra in html
