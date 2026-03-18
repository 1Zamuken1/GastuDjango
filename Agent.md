# AGENT.md — Contexto del proyecto GastuApp

> Documento de referencia para agentes IA y colaboradores.
> Mantener actualizado al final de cada sesión de trabajo significativa.
> Última actualización: 2026-03-10

---

## 1. Descripción general

**GastuApp** es un sistema de gestión financiera personal desarrollado como proyecto formativo en SENA (ficha 3065834-1). Originalmente construido en Spring Boot, fue migrado a Django 5.2. Sirve como portafolio profesional del equipo y como proyecto real con usuarios finales.

**Repositorio:** https://github.com/1Zamuken1/GastuDjango.git  
**Objetivo inmediato:** completar la plataforma y obtener práctica profesional.

---

## 2. Stack técnico

| Capa | Tecnología |
|---|---|
| Backend | Django 5.2 |
| Base de datos | PostgreSQL vía Supabase (Transaction pooler, puerto 6543) |
| ORM | Django ORM nativo |
| Frontend | Django Templates + Tailwind CDN + HTMX (pendiente) |
| Íconos | Lucide (CDN unpkg) |
| Fuentes | Plus Jakarta Sans (display) + DM Sans (cuerpo) |
| Auth | Sistema nativo de Django con vistas propias |
| IA / Agente | Gemini Flash (Google AI Studio, free tier) — Groq como fallback |
| Driver DB | `psycopg[binary]==3.2.10` (psycopg2-binary incompatible con Python 3.14) |
| Python | 3.14 |
| Entorno | Windows, venv en `GastuDjango/venv/` |

---

## 3. Estructura de apps

```
GastuDjango/
├── gastu_django/          # Configuración central (settings, urls, wsgi)
├── usuarios/              # Modelo Usuario personalizado, login, register
├── movimientos/           # Modelo Movimiento — CRUD completo (ingresos y egresos)
├── categorias/            # Modelo Categoria — CRUD completo (extraída de movimientos)
├── ahorros/               # Pendiente — otro integrante del equipo
├── planificacion/         # Pendiente — otro integrante del equipo
├── presupuesto/           # Modelo Presupuesto — otro integrante del equipo
├── notificaciones/        # Modelo Notificacion — lógica de alertas automáticas
├── dashboard/             # Modelo ResumenMensual — vista principal post-login
├── agente/                # Pendiente — integración IA
├── landing/               # Landing page pública (sin auth)
└── templates/
    ├── base_app.html      # Layout global con topbar + sidenav (TODAS las vistas app usan este)
    └── registration/
        └── login.html     # Redirige a usuarios/login.html
```

---

## 4. Configuración crítica

### settings.py

```python
LOGIN_REDIRECT_URL  = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL           = '/login/'

DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}
# Requerido para Transaction pooler de Supabase (deshabilita prepared statements)
DATABASES['default']['OPTIONS'] = {'prepare_threshold': None}
```

### .env (no commitear — compartir por canal privado)

```env
SECRET_KEY=django-insecure-cambia-esto
DEBUG=True
DATABASE_URL=postgresql://postgres.hazefwuhlqytkhafdcux:[PASSWORD]@aws-1-sa-east-1.pooler.supabase.com:6543/postgres
```

**Importante:** usar puerto `6543` (Transaction pooler), NO el 5432 (Session pooler). El `DATABASE_URL` debe empezar con `postgresql://`, no `postgres://`.

### gastu_django/urls.py (estado actual)

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('landing.urls', namespace='landing')),
    path('', include('usuarios.urls')),                          # login, logout, register — sin namespace
    path('', include('movimientos.urls', namespace='movimientos')),
    path('categorias/', include('categorias.urls', namespace='categorias')),
    path('presupuesto/', include('presupuesto.urls')),           # sin namespace aún
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
]
```

---

## 5. Autenticación

- Vistas propias en `usuarios/views.py`: `login_view`, `register_view`, `logout_view`
- URLs sin namespace: `{% url 'login' %}`, `{% url 'register' %}`, `{% url 'logout' %}`
- Templates: `usuarios/templates/usuarios/login.html` y `register.html`
- Post-login siempre redirige a `dashboard:home`
- `register.html` tiene barra de seguridad de contraseña con 4 criterios (longitud, mayúscula, número, especial), toggle de visibilidad, e indicador de coincidencia

---

## 6. Sistema de templates — layout global

### `templates/base_app.html`

Todas las vistas de la aplicación (post-login) extienden este archivo. **No crear layouts locales por app.**

**Bloques disponibles:**

```html
{% block title %}{% endblock %}          <!-- <title> de la página -->
{% block extra_head %}{% endblock %}     <!-- CSS adicional por vista -->
{% block page_title %}{% endblock %}     <!-- Título en topbar -->
{% block page_subtitle %}{% endblock %}  <!-- Subtítulo en topbar -->
{% block content %}{% endblock %}        <!-- Contenido principal -->
{% block scripts %}{% endblock %}        <!-- JS adicional al final del body -->

<!-- Bloques de estado activo en la sidenav -->
{% block nav_dashboard %}{% endblock %}
{% block nav_ingresos %}{% endblock %}
{% block nav_egresos %}{% endblock %}
{% block nav_presupuestos %}{% endblock %}
{% block nav_perfil %}{% endblock %}
{% block nav_categorias %}{% endblock %}
```

**Cómo usar en un módulo nuevo:**

```html
{% extends "base_app.html" %}

{% block nav_egresos %}active{% endblock %}
{% block page_title %}Egresos{% endblock %}
{% block page_subtitle %}Historial de gastos{% endblock %}

{% block content %}
  <!-- contenido aquí -->
{% endblock %}
```

**Regla importante:** nunca escribir `{% if %}`, `{{ }}` ni `{%` dentro de comentarios CSS (`/* */`) dentro de bloques `<style>` — Django los parsea y lanza `TemplateSyntaxError`. Los condicionales Django solo van en atributos `class=""`, nunca en `style=""`.

### Sistema de diseño

**Paleta principal:**

```css
--emerald:       #10b981;   /* acento principal */
--emerald-dark:  #059669;
--emerald-light: #ecfdf5;
--slate-900:     #0f172a;
--slate-700:     #334155;
--slate-500:     #64748b;
--border:        #e2e8f0;
--white:         #ffffff;
```

**Fondo del body:** `#e8edf2` (gris azulado, da contraste a las cards blancas)

**Tipografía:**
- Display / títulos: `Plus Jakarta Sans` (700–900)
- Cuerpo: `DM Sans` (300–500)

**Clases globales disponibles:**
- `.app-card` — card blanca con borde y sombra
- `.btn-primary` — botón verde emerald
- `.btn-ghost` — botón secundario con borde
- `.font-display` — aplica Plus Jakarta Sans

### Colores de la sidenav por sección

Cada ítem de navegación tiene una clase `nav-item--xxx` que define su propio color de hover y estado activo:

| Ítem | Clase | Color activo |
|---|---|---|
| Dashboard | `nav-item--dashboard` | Índigo `#6366f1` |
| Ingresos | `nav-item--ingresos` | Emerald `#10b981` |
| Egresos | `nav-item--egresos` | Orange `#f97316` |
| Ahorros | `nav-item--ahorros` | Amber `#d97706` |
| Planificaciones | `nav-item--planificaciones` | Blue `#1d4ed8` |
| Presupuestos | `nav-item--presupuestos` | Violet `#7c3aed` |
| Agente | `nav-item--agente` | Sky `#0ea5e9` |
| Mi perfil | `nav-item--dashboard` | (mismo que Dashboard) |
| Categorías (admin) | `nav-item--categorias` | Purple `#a855f7` |

El estado activo se activa poniendo `active` en el bloque correspondiente del template hijo.

---

## 7. App dashboard

### Modelo: `ResumenMensual`

Snapshot mensual de las finanzas del usuario. Se actualiza automáticamente vía signals en `movimientos`.

### Vista: `dashboard/views.py` → `home_view`

Contexto que inyecta al template:

| Variable | Descripción |
|---|---|
| `resumen` | Objeto `ResumenMensual` del mes actual |
| `total_ingresos` | Decimal |
| `total_egresos` | Decimal |
| `disponible` | Decimal (ingresos - egresos) |
| `ingreso_neto` | Decimal (puede ser negativo) |
| `hay_deficit` | Boolean |
| `ultimos_movimientos` | Últimos 6 movimientos con `select_related('categoria')` |
| `chart_data_json` | JSON string — top 5 egresos por categoría para el gráfico de barras |
| `notificaciones_count` | Int — notificaciones sin leer |
| `ultimas_notificaciones` | Últimas 4 notificaciones |
| `mes_nombre` | Str (ej. "Marzo") |
| `anio` | Int |
| `hoy` | `date.today()` |

### Template: `dashboard/templates/dashboard/home.html`

- Extiende `base_app.html`
- Activa `{% block nav_dashboard %}active{% endblock %}`
- Secciones: saludo + badge de estado, 4 stat cards, gráfico de barras + panel de alertas, tabla de últimos movimientos
- Gráfico de barras renderizado con JS puro a partir de `chart_data_json` (no usa Chart.js)
- Los datos del gráfico van en `<script id="chart-data" type="application/json">` para evitar conflictos con el linter

---

## 8. App movimientos

### Modelo: `Movimiento`

Campos relevantes: `usuario`, `tipo` (`INGRESO` / `EGRESO`), `monto`, `descripcion`, `fecha_registro`, `categoria` (FK a `categorias.Categoria`).

### URLs (namespace `movimientos`)

```python
movimientos:lista_ingresos    # GET — lista filtrada por tipo=INGRESO
movimientos:lista_egresos     # GET — lista filtrada por tipo=EGRESO
movimientos:crear_ingreso     # GET/POST
movimientos:crear_egreso      # GET/POST
```

### Templates

Extienden `base_app.html` con los bloques `nav_ingresos` o `nav_egresos` activos según corresponda.

### Bug conocido

`movimientos/views.py` y `movimientos/admin.py` importan `Categoria` desde `movimientos.models` (ya no existe ahí — fue extraída a `categorias.models`). Pendiente de corregir.

---

## 9. App categorias

Extraída de `movimientos` para ser compartida por todo el sistema.  
Solo visible en la sidenav para `request.user.is_staff`.

**URLs (namespace `categorias`):**
```python
categorias:lista_categorias
```

---

## 10. App notificaciones

Servicio `notificaciones/services.py` con función `analizar_movimiento` — disparada por signals de `movimientos`. Crea alertas automáticas en base a reglas (déficit, egreso grande, etc.).

**Bug conocido:** `analizar_movimiento` está definida dos veces en el archivo. Pendiente de corregir.

**Modelo `Notificacion`:** campos `titulo`, `tipo` (`DEFICIT`, `EGRESO_GRANDE`, otros), `leida` (Boolean), `fecha_creacion`.

---

## 11. App usuarios

### Modelo

Usuario personalizado que extiende `AbstractUser`. Campos adicionales: `telefono` (opcional).

### Form: `UsuarioCreationForm`

Campos: `username`, `email`, `telefono`, `password1`, `password2`.

### Seguridad actual

- SQL injection: cubierta por ORM (queries parametrizadas)
- XSS: cubierto por auto-escape de Django templates
- CSRF: tokens en todos los forms
- Rate limiting en login: **pendiente** (requiere `django-ratelimit`)

---

## 12. App presupuesto

Desarrollada por otro integrante del equipo. URL de lista: `listar_presupuestos` (sin namespace aún). La sidenav apunta a esta URL.

---

## 13. Apps pendientes

| App | Estado | Responsable |
|---|---|---|
| `ahorros` | Sin implementar | Otro integrante |
| `planificacion` | Sin implementar | Otro integrante |
| `agente` | Sin implementar | Zamuken (integración Gemini Flash) |

Los ítems de sidenav correspondientes tienen clase `disabled` y badge "Pronto".

---

## 14. Landing page

App `landing` con `namespace='landing'`. Template principal: `landing/templates/landing/home.html`.

- Extiende su propio `landing/base.html` (distinto de `base_app.html`)
- Tema claro con blobs decorativos, animaciones CSS
- CTA "Ya tengo cuenta" apunta a `{% url 'login' %}`
- Fix aplicado: `body { overflow-x: hidden }` para evitar scroll horizontal por los blobs

---

## 15. Bugs conocidos y pendientes técnicos

| Archivo | Bug | Estado |
|---|---|---|
| `movimientos/views.py` | Importa `Categoria` desde `movimientos.models` | Pendiente |
| `movimientos/admin.py` | Importa `Categoria` desde `movimientos.models` | Pendiente |
| `movimientos/signals.py` | `actualizar_resumen_al_guardar` y `actualizar_resumen_al_eliminar` definidas dos veces | Pendiente |
| `notificaciones/services.py` | `analizar_movimiento` definida dos veces | Pendiente |
| `usuarios/views.py` | Rate limiting en login no implementado | Pendiente |

---

## 16. Setup del proyecto desde cero

```bash
git clone https://github.com/1Zamuken1/GastuDjango.git
cd GastuDjango
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
# Solicitar .env al equipo (nunca está en el repo)
python manage.py migrate
python manage.py loaddata movimientos/fixtures/categorias.json
python manage.py runserver
```

---

## 17. Convenciones del proyecto

- **Commits:** en español, concisos, con prefijo convencional (`feat:`, `fix:`, `perf:`, `refactor:`)
- **Docstrings:** usar docstrings Python en lugar de comentarios `#` en código de negocio
- **Arquitectura:** orientada a objetos, principios SOLID, modelos con clase base abstracta donde aplique
- **Sin emojis** en documentación técnica ni docstrings
- **CSS:** nunca escribir `{% %}` o `{{ }}` de Django dentro de `style=""` — usar clases CSS predefinidas y aplicar condicionales en `class=""`
- **Templates:** nunca crear layouts locales por app si ya existe `base_app.html`