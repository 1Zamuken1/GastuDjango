# AGENT.md — Contexto del proyecto GastuApp

> Documento de referencia para agentes IA y colaboradores.
> Mantener actualizado al final de cada sesión de trabajo significativa.
> Última actualización: 2026-06-03

---

## 1. Descripción general

**GastuApp** es un sistema de gestión financiera personal desarrollado como proyecto formativo en SENA (ficha 3065834-1). Originalmente construido en Spring Boot, fue migrado a Django 5.2. Sirve como portafolio profesional del equipo y como proyecto real con usuarios finales.

**Repositorio:** https://github.com/1Zamuken1/GastuDjango.git  
**Deadline de entrega del equipo:** 26 de abril de 2026  
**Objetivo inmediato:** completar la plataforma y obtener práctica profesional.

---

## 2. Stack técnico

| Capa | Tecnología |
|---|---|
| Backend | Django 5.2 |
| Base de datos | PostgreSQL vía Supabase o SQLite local (conmutables) |
| ORM | Django ORM nativo |
| Frontend | Django Templates + django-tailwind (Tailwind CSS 4.0) + ApexCharts + Lucide |
| Íconos | Lucide (CDN unpkg / local) |
| Fuentes | Plus Jakarta Sans (display) + DM Sans (cuerpo) |
| Auth | Sistema nativo de Django con vistas propias |
| IA / Agente | Gemini Flash (Google AI Studio, free tier) — Groq como fallback |
| Driver DB | `psycopg[binary]==3.2.10` (psycopg2-binary incompatible con Python 3.14) |
| Python | 3.14 |
| Entorno | Windows, venv en `GastuDjango/venv/` |
| Alertas JS | SweetAlert2 vía `static/js/gastu_alerts.js` (`window.GastuAlerts`) — disponible en TODAS las páginas (base_app.html y base_admin.html) |

---

## 3. Estructura de apps

```
GastuDjango/
├── gastu_django/          # Configuración central (settings, urls, wsgi)
├── usuarios/              # Modelo Usuario personalizado, login, register, perfil — 95%
├── movimientos/           # Modelo Movimiento — CRUD completo — 100%
├── categorias/            # Modelo Categoria — CRUD completo — 100%
├── ahorros/               # Metas de ahorro y aportes — 95%
├── programaciones/        # Movimientos recurrentes y programados — 95%
├── presupuesto/           # Planificación de presupuestos mensuales — 95%
├── notificaciones/        # Alertas automáticas y centro de notificaciones — 80%
├── dashboard/             # Vista principal, estadísticas y navegación — 100%
├── agente_financiero/     # Integración con IA (Gemini/Groq) para análisis y chat — 97%
├── landing/               # Landing page pública — 100%
├── panel_admin/           # Dashboard administrativo para gestión de datos — 90%
├── historial/             # Sistema de auditoría y log de acciones — 100%
├── theme/                 # Aplicación de Tailwind CSS (configuración y assets)
└── templates/             # Layouts globales y plantillas compartidas
```

---

## 4. Configuración crítica

### settings.py

```python
LOGIN_REDIRECT_URL  = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL           = '/login/'

# ── SQLite vs PostgreSQL ──────────────────────────────────────
# MODO ACTIVO: SQLite local (USE_SQLITE=True en .env)
# Para volver a Supabase: cambiar USE_SQLITE=False en .env
# ──────────────────────────────────────────────────────────────

if os.getenv('USE_SQLITE', 'False') == 'True':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.getenv('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    # Requerido para Transaction pooler de Supabase
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
    path('sitemap.xml', sitemap, ...),
    path('robots.txt', TemplateView.as_view(...)),
    path('admin/', admin.site.urls),
    path('', include('landing.urls', namespace='landing')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('', include('usuarios.urls')),
    path('', include('movimientos.urls', namespace='movimientos')),
    path('categorias/', include('categorias.urls', namespace='categorias')),
    path('admin-panel/', include('panel_admin.urls', namespace='panel_admin')),
    path('ahorros/', include('ahorros.urls', namespace='ahorros')),

    # APIs del módulo de planificación financiera
    path('api/', include('categorias.api_urls')),
    path('api/', include('presupuesto.api_urls')),            # CRUD presupuestos vía ViewSet
    path('api/', include('programaciones.api_urls')),         # CRUD programaciones + pendientes/ejecutar
    path('api/', include('agente_financiero.api_urls')),      # Chat, limpiar, alertas

    # Módulos web del módulo de planificación financiera
    path('presupuesto/', include('presupuesto.urls')),        # SPA de presupuestos
    path('programaciones/', include('programaciones.urls')),  # SPA de programaciones
    path('agente_financiero/', include('agente_financiero.urls')),  # Chat con GASTU

    path('notificaciones/', include('notificaciones.urls', namespace='notificaciones')),
    path('historial/', include('historial.urls', namespace='historial')),
    path('auth/', include('allauth.urls')),
    path('__reload__/', include('django_browser_reload.urls')),
]
```

---

## 5. Autenticación

- Vistas propias en `usuarios/views.py`: `login_view`, `register_view`, `logout_view`
- URLs sin namespace: `{% url 'login' %}`, `{% url 'register' %}`, `{% url 'logout' %}`
- Templates: `usuarios/templates/usuarios/login.html` y `register.html`
- Post-login siempre redirige a `dashboard:home`
- `register.html` tiene barra de seguridad de contraseña con 4 criterios (longitud, mayúscula, número, especial), toggle de visibilidad, e indicador de coincidencia
- Rate limiting en login: **pendiente** (requiere `django-ratelimit`)

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
{% block nav_ahorros %}{% endblock %}
{% block nav_programaciones %}{% endblock %}
{% block nav_presupuestos %}{% endblock %}
{% block nav_perfil %}{% endblock %}
{% block nav_categorias %}{% endblock %}
{% block nav_agente %}{% endblock %}
{% block nav_panel_admin %}{% endblock %}
```

### Sistema de diseño — paleta principal

```css
--emerald:       #10b981;   /* acento principal — ingresos */
--emerald-dark:  #059669;
--emerald-light: #ecfdf5;
--scarlet:       #e11d48;   /* acento egresos */
--scarlet-dark:  #be123c;
--slate-900:     #0f172a;
--slate-700:     #334155;
--slate-500:     #64748b;
--border:        #e2e8f0;
--white:         #ffffff;
```

**Nota de color:** los egresos usan escarlata `#e11d48`, NO naranja. El naranja quedó descartado definitivamente. Aplicado en `egresos.css`, `datepicker.css`, `egresos.js`, `base_app.html`, `dashboard.css` y `dashboard.js`.

**Fondo del body:** `#e8edf2` (gris azulado, da contraste a las cards blancas)

**Tipografía:**
- Display / títulos: `Plus Jakarta Sans` (700–900)
- Cuerpo: `DM Sans` (300–500)

**Clases globales disponibles:**
- `.app-card` — card blanca con borde y sombra
- `.btn-primary` — botón verde emerald
- `.btn-ghost` — botón secundario con borde
- `.font-display` — aplica Plus Jakarta Sans

- **Tailwind CSS**: Gestionado localmente vía la app `theme`. Requiere Node.js.
- **Comando de desarrollo**: `python manage.py tailwind start` (compilador PostCSS en modo watch).
- **Importante**: No usar Tailwind CDN en el layout base.

### Reglas anti-bugs de Django Templates

- Nunca escribir `{% if %}`, `{{ }}` ni `{%` dentro de comentarios CSS (`/* */`) ni dentro de bloques `<style>` — Django los parsea y lanza `TemplateSyntaxError`.
- Los condicionales Django solo van en atributos `class=""`, nunca en `style=""`.
- Los datos para JavaScript se pasan via atributos `data-` en el HTML. Nunca embeber variables Django directamente en bloques `<script>`.
- Separación estricta: HTML en `.html`, CSS fuente en `theme/static_src/src/styles.css`, JS en archivos `.js`.

### Colores de la sidenav por sección

| Ítem | Clase | Color activo |
|---|---|---|
| Dashboard | `nav-item--dashboard` | Índigo `#6366f1` |
| Ingresos | `nav-item--ingresos` | Emerald `#10b981` |
| Egresos | `nav-item--egresos` | Scarlet `#e11d48` |
| Ahorros | `nav-item--ahorros` | Amber `#d97706` |
| Planificaciones | `nav-item--planificaciones` | Blue `#1d4ed8` |
| Presupuestos | `nav-item--presupuestos` | Violet `#7c3aed` |
| Agente | `nav-item--agente` | Sky `#0ea5e9` |
| Mi perfil | `nav-item--perfil` | Teal `#0d9488` |
| Categorías (admin) | `nav-item--categorias` | Purple `#a855f7` |

### Toggle del sidebar

Dos mecanismos independientes:

- **Desktop / tablet** (`> 767px`): botón dentro del sidebar con iconos `panel-left-close` / `panel-left-open` y label "Contraer menú". Activa modo `mini` (solo iconos). Estado persistido en `localStorage`.
- **Mobile** (`≤ 767px`): botón hamburguesa `#sidebar-toggle-mobile` en el topbar. Abre el sidebar con overlay. El `sidebar-header` se oculta con `display:none` en mobile.

### Responsive — breakpoints implementados

Los breakpoints están en `dashboard/static/dashboard/css/dashboard.css` y en `base_app.html`:

| Breakpoint | Cambios principales |
|---|---|
| `≤ 1180px` | Grids pasan a columna única |
| `≤ 1023px` | Tablet: carousel 2 slides |
| `≤ 767px` | Mobile: 1 slide, gráficos reducidos, tabla simplificada, nav-meses compacto, quick-add oculto |
| `≤ 479px` | Mobile pequeño: nav-meses con wrap |

---

## 7. App dashboard — estado actual (90%)

### Modelo: `ResumenMensual`

Snapshot mensual de las finanzas del usuario. Se actualiza automáticamente vía signals en `movimientos`. Los ahorros se calculan directamente desde `AporteAhorro` con queries `fecha_registro__lte=ultimo_dia` porque `ResumenMensual.total_ahorros` siempre devuelve 0 (signals no conectados aún).

### Vista: `dashboard/views.py`

- `home_view`: acepta query params `?mes=&anio=`. Responde JSON si `X-Requested-With: XMLHttpRequest`, HTML si es carga directa.
- `meses_disponibles`: endpoint GET que devuelve los meses con `ResumenMensual` registrado para el usuario. Se cachea en JS en el primer request.
- `tendencia_mes`: endpoint GET con datos del gráfico de tendencia. Devuelve `detalle_ing` y `detalle_egr` — dicts `{dia: [{nombre, monto}]}` para tooltip con desglose por categoría.
- `_build_context()`: helper interno que construye el contexto de la vista principal.

### URLs (namespace `dashboard`)

```python
dashboard:home
dashboard:meses_disponibles
dashboard:tendencia_mes
```

### Template: `dashboard/templates/dashboard/home.html`

Secciones:
- Saludo + badge de estado financiero
- Controles de navegación de meses (← mes anterior | badge "Histórico" cuando no es el mes actual | mes siguiente →)
- 4 stat cards (ingresos, egresos, disponible, ahorros) con IDs para actualización sin recarga
- Gráfico de tendencia mensual (ApexCharts, line chart) con tooltip custom de desglose por categoría y controles de zoom
- Gráfico de distribución de egresos (ApexCharts, donut chart)
- Tabla de últimos movimientos
- Panel de notificaciones

### JavaScript: `dashboard/static/dashboard/js/dashboard.js`

- Navegación de meses completa con `fetch` y actualización parcial del DOM (sin recarga).
- `AbortController` en cada llamada a `iniciarTendencia()` para cancelar listeners anteriores y evitar duplicación de eventos de zoom.
- `sincronizarNavBotones()` se llama dentro de `initPrimerMes()` para evitar race condition.
- Alturas de gráficos dinámicas según `window.innerWidth` al renderizar: tendencia 270 / 220 / 200px, pie 280 / 240 / 220px.
- Tooltip custom con desglose por categoría por día en el gráfico de tendencia.

---

## 8. App movimientos — estado actual (95%)

### Modelo: `Movimiento`

Hereda de `ModeloBase` (definida en `movimientos/models.py`). Campos: `usuario` (FK), `categoria` (FK → `categorias.Categoria`), `tipo` (`INGRESO` / `EGRESO`), `monto`, `descripcion`, `fecha_registro` (auto_now_add).

### Señales

`movimientos/signals.py` conecta `post_save` y `post_delete` de `Movimiento` a:
- `dashboard.services.actualizar_resumen` — recalcula `ResumenMensual`
- `notificaciones.services.analizar_movimiento` — genera alertas automáticas

### URLs (namespace `movimientos`)

```python
# Vistas HTML
movimientos:ingresos                          # GET
movimientos:egresos                           # GET

# Endpoints CRUD del frontend (FormData + sesión Django)
movimientos:guardar_movimiento                # POST — crear
movimientos:editar_movimiento    pk=<int>     # POST — editar
movimientos:eliminar_movimiento  pk=<int>     # POST — eliminar

# Endpoints de consulta del frontend
movimientos:registros_por_categoria           # GET
movimientos:resumen_movimientos               # GET
movimientos:buscar_registros                  # GET

# Exportación
movimientos:exportar_csv                      # GET
movimientos:exportar_excel                    # GET
movimientos:exportar_pdf                      # GET

# API REST para agente_financiero (JSON puro)
movimientos:api_listar                        # GET  /movimientos/api/listar/
movimientos:api_categorias                    # GET  /movimientos/api/categorias/
movimientos:api_crear                         # POST /movimientos/api/crear/
movimientos:api_editar           pk=<int>     # POST /movimientos/api/editar/<pk>/
movimientos:api_eliminar         pk=<int>     # POST /movimientos/api/eliminar/<pk>/
```

### API REST para el agente (`movimientos/views_api.py`)

Archivo separado de `views.py`. No modifica ninguna vista existente.

**GET `/movimientos/api/listar/`**

Parámetros: `tipo` (INGRESO|EGRESO|AMBOS), `mes`, `anio`, `categoria`, `fecha_desde`, `fecha_hasta`, `page`, `page_size` (máx 200). Si se envía `fecha_desde` o `fecha_hasta`, ignora `mes`/`anio`.

Respuesta: `{ok, movimientos[], paginacion{}, resumen{total_ingresos, total_egresos, balance}, filtros_aplicados{}}`.

**GET `/movimientos/api/categorias/`**

Parámetros: `tipo`. Respuesta: `{ok, categorias[{id, nombre, tipo}]}`.

**POST `/movimientos/api/crear/`**

Body JSON: `{tipo, categoria, monto, descripcion?}`. Valida disponible para egresos. HTTP 201 en éxito.

**POST `/movimientos/api/editar/<pk>/`**

Body JSON parcial: solo los campos que se quieran cambiar (`categoria?`, `monto?`, `descripcion?`). El tipo no se puede cambiar. Verifica propiedad con `get_object_or_404(..., usuario=request.user)`.

**POST `/movimientos/api/eliminar/<pk>/`**

Sin body. Verifica propiedad. Respuesta: `{ok, id}`.

**Autenticación de la API:** todos los endpoints requieren sesión Django activa (`@login_required`). Los POST requieren el header `X-CSRFToken` con el valor de la cookie `csrftoken`. Si el agente opera sin pasar por una vista HTML previa, hay que agregar `@csrf_exempt` a los endpoints de escritura o implementar autenticación por token.

### Vistas de página: ingresos y egresos

Patrón idéntico en ambas. Cada vista:
1. Calcula totales del mes actual con `_build_categorias_con_totales()`.
2. Renderiza un grid de cards por categoría con totales, porcentaje y barra de progreso.
3. CRUD completo en modales (sin recarga de página): crear, editar, eliminar via fetch.
4. Modal de registros por categoría con paginación (10 por página).
5. Picker visual de categorías (modal secundario) en lugar de `<select>` nativo.
6. Buscador con debounce que filtra DOM localmente y confirma con el backend.
7. Exportación a CSV, Excel y PDF via modal de parámetros con datepicker y selección de categorías.

### Componentes JS

- `movimientos/static/movimientos/js/egresos.js` — lógica completa de egresos
- `movimientos/static/movimientos/js/ingresos.js` — lógica completa de ingresos (espejo de egresos con colores emerald)
- `movimientos/static/movimientos/js/datepicker.js` — `MiniDatepicker` — clase propia, no depende de librerías externas. Soporta variante `acento: 'egreso'` para colores scarlet.

### Pendientes del módulo (el 5% restante)

- Responsive de las vistas ingresos y egresos (stats-hero, toolbar, grid de categorías, modales). El dashboard ya está responsive; estas vistas todavía no.

---

## 9. App categorias — estado actual (100%)

Extraída de `movimientos` para ser compartida por todo el sistema. Solo visible en la sidenav para `request.user.is_staff`.

**URLs (namespace `categorias`):**
```python
categorias:lista_categorias
```

---

## 10. App notificaciones — estado actual (100%)

Aplicación completamente funcional y fuertemente refactorizada. Utiliza una arquitectura avanzada basada en analizadores (`analyzers/`), chequeos (`checks/`) y un despachador (`dispatcher.py`) para generar alertas inteligentes en tiempo real, conectada mediante WebSockets (`consumers.py`).

**Modelos (`notificaciones/models.py`):**
- `Notificacion`: Almacena la alerta. Cuenta con múltiples tipos (`Tipo`) que cubren desde umbrales y déficits hasta patrones inusuales, proyecciones de sobregasto y recordatorios de ahorro.
- Se ha integrado un sistema de categorización por `Modulo` (INGRESOS, EGRESOS, AHORROS, etc.) que permite filtrar las alertas en la interfaz.

**Vistas y APIs (`notificaciones/views.py`):**
- `notificaciones_json`: Endpoint GET que devuelve las notificaciones del usuario paginadas y filtradas por módulo, junto con recuentos de no leídas.
- `notificaciones_marcar_leidas`: Endpoint POST para marcar notificaciones individuales o por módulo como leídas.

**Resolución de Bugs Antiguos:**
- El archivo antiguo `services.py` fue eliminado por completo, resolviendo la deuda técnica y la duplicidad de funciones.
- La interfaz de usuario ya está completamente soportada mediante los endpoints REST y la conexión asíncrona de WebSockets (Django Channels).

---

## 11. App ahorros — estado actual (100%)

Aplicación completamente funcional e integrada. Permite crear metas de ahorro, generar cuotas automáticas basadas en la frecuencia elegida, y registrar aportes que actualizan el dashboard y el historial en tiempo real.

**Modelos (`ahorros/models.py`):**
- `AhorroMeta`: Define la meta de ahorro (monto, fecha, frecuencia, cantidad de cuotas). **Nota de deuda técnica:** Aún no hereda de `ModeloBase` (hereda directamente de `models.Model`).
- `AporteAhorro`: Representa las cuotas (aportes) generadas automáticamente. Estados: `PENDIENTE`, `APORTADO`, `PERDIDO`.
*Nota: Los campos ya fueron migrados a `snake_case` correctamente.*

**Integración (Signals y Dashboard):**
- **Dashboard:** Los signals en `ahorros/signals.py` actualizan correctamente `ResumenMensual` (`total_ahorros`, `ingreso_neto`, `disponible`) cada vez que se registra o elimina un aporte (`estado_ap == 'APORTADO'`).
- **Historial:** Todas las creaciones/ediciones/eliminaciones de metas y aportes se auditan automáticamente creando registros en `historial.models.AccionHistorial` bajo `ModuloChoices.AHORROS`.

**Vistas y Servicios:**
- Incluye vistas para listar, crear, editar, eliminar metas y registrar aportes.
- Módulo integrado para exportar a CSV, Excel y PDF (`views_exportar.py`).
- Capa de servicios (`services.py`) maneja el recálculo dinámico de fechas, montos y estados de cuotas tras ediciones o abonos extraordinarios.

---

## 12. App usuarios — estado actual (95%)

### Modelo

Usuario personalizado que extiende `AbstractUser`. Campos adicionales: `telefono` (opcional).

### Form: `UsuarioCreationForm`

Campos: `username`, `email`, `telefono`, `password1`, `password2`.

### Lo que funciona

- Login, registro, logout y recuperación de contraseña vía correo.
- Plantillas personalizadas de correo (cuenta activa e inactiva).
- `register.html` con barra de seguridad de contraseña (4 criterios: longitud, mayúscula, número, especial), toggle de visibilidad, indicador de coincidencia de contraseñas.
- Vista de Perfil (`/perfil/`) completa: edición de datos personales, cambio de contraseña, panel de preferencias de notificaciones y eliminación de cuenta.

### Pendiente (el 5% restante)

- Rate limiting en login (`django-ratelimit`).

---

## 13. App presupuesto — estado actual (95%)

### Modelo: `Presupuesto`

| Campo | Tipo | Descripción |
|---|---|---|
| `limite` | `DecimalField` | Máximo permitido para el período |
| `fecha_inicio` | `DateField` | Inicio del período presupuestal |
| `fecha_fin` | `DateField` | Fin del período presupuestal |
| `isActivo` | `BooleanField` | **camelCase** — pendiente de migrar a `is_activo` |
| `categoria` | FK → `categorias.Categoria` | Categoría asociada |
| `usuario` | FK → `usuarios.Usuario` | Propietario |

### API REST vía ViewSet (`/api/presupuestos/`)

CRUD completo con `PresupuestoViewSet` + 3 endpoints custom:
- `GET /api/presupuestos/alertas/` — estado de alerta de presupuestos activos
- `GET /api/presupuestos/con_estado/` — todos con `gastado`, `porcentaje`, `alerta`
- `POST /api/presupuestos/verificar_vencidos/` — desactiva expirados

### Servicios (`services.py`)

- `_qs_con_total_gastado(qs)` — anota gasto real vía subquery de `Movimiento`
- `desactivar_presupuestos_vencidos(usuario)` — desactiva los que tienen `fecha_fin < hoy`
- `calcular_alerta_presupuesto(p)` — calcula `(total_gastado, porcentaje)`
- `nivel_alerta(porcentaje)` — mapea % a nivel: baja, nivel_50..95, critica
- `obtener_estados_presupuestos(usuario)` — estados completos de presupuestos activos

### Señales

- `post_save` → `auditar_presupuesto_guardar` (CREACION / EDICION en `AccionHistorial`)
- `post_delete` → `auditar_presupuesto_eliminar` (ELIMINACION)

### Tests: 217 líneas, pytest

### Bugs conocidos
- **Sin `@login_required`** en `views.py` (la vista web es accesible sin autenticación)
- **`isActivo`** en camelCase — migrar a `is_activo`
- **`con_estado`** no calcula gastado para presupuestos inactivos (siempre 0)
- **Admin vacío** — modelo no registrado en `admin.py`

---

## 14. App programaciones — estado actual (95%)

### Modelo: `Programacion`

| Campo | Tipo | Descripción |
|---|---|---|
| `monto_programado` | `DecimalField` | Monto a ejecutar |
| `tipo` | `CharField` | `INGRESO` / `EGRESO` (copiado desde `categoria.tipo`) |
| `descripcion` | `CharField` | Opcional, 100 caracteres |
| `fecha_inicio` | `DateField` | Inicio de la recurrencia |
| `fecha_fin` | `DateField` | Fin de la recurrencia (opcional) |
| `frecuencia` | `CharField` | DIARIO, SEMANAL, QUINCENAL, MENSUAL, BIMESTRAL, TRIMESTRAL, SEMESTRAL, ANUAL |
| `proxima_ejecucion` | `DateField` | Próxima fecha de ejecución calculada |
| `activo` | `BooleanField` | Se desactiva automáticamente al vencer |
| `categoria` | FK → `categorias.Categoria` | Categoría asociada |
| `usuario` | FK → `usuarios.Usuario` | Propietario |

### API REST vía ViewSet (`/api/programaciones/`)

CRUD completo con `ProgramacionViewSet` + 2 endpoints custom:
- `GET /api/programaciones/pendientes/` — lista programaciones listas para ejecutar hoy
- `POST /api/programaciones/{id}/ejecutar/` — acepta o rechaza (`{"accion": "aceptar"|"rechazar"}`)

### Servicios (`services.py`)

- `calcular_proxima_fecha(prog, hoy)` — próxima ejecución usando `relativedelta` según frecuencia
- `desactivar_si_vencida(prog, hoy)` — desactiva si `fecha_fin` ya pasó
- `obtener_pendientes(usuario)` — recolecta programaciones listas para ejecutar
- `ejecutar_programacion(prog, accion, request)` — crea `Movimiento` y avanza `proxima_ejecucion`
- `DELTA_MAP` — mapeo frecuencia → `relativedelta`

### Señales

- `post_save` → `auditar_programacion_guardar`
- `post_delete` → `auditar_programacion_eliminar`

### Templates: SPA completa

- `base_programacion.html` → extiende `base_app.html`
- `listar_programaciones.html` — stats hero, grid de cards, modales CRUD, verificación de pendientes al cargar

### Tests: 20 tests pytest (servicios, serializers, API)

---

## 15. App agente_financiero — estado actual (97%)

Integración con **Groq Cloud** (`llama-3.3-70b-versatile`) para análisis financiero mediante tool calling y alertas personalizadas.

### Modelos

- `MensajeChat` — historial de la conversación (`usuario`, `rol`, `contenido`, `creado_en`)
- `AlertaDiaria` — alertas generadas automáticamente con control de frecuencia

### APIs REST (`/api/agente/`)

- `GET/POST /api/agente/chat/` — obtener historial (GET) o enviar mensaje al agente (POST)
- `POST /api/agente/limpiar/` — eliminar todo el historial del usuario
- `GET/POST /api/agente/alertas/` — obtener alertas (GET) o marcar como vistas (POST)

### Componentes backend

- **`RecolectorDatos`** (`recolector.py`) — reúne resumen mensual, últimos movimientos, metas de ahorro, presupuestos y programaciones del usuario
- **`construir_prompt()`** (`prompt_builder.py`) — arma el system prompt con identidad GASTU + contexto financiero
- **`EjecutorHerramientas`** (`herramientas.py`) — 3 herramientas invocables por el LLM:
  - `obtener_movimientos(tipo, mes, anio, categoria, limite)` — filtrar movimientos
  - `obtener_resumen_periodo(mes, anio)` — agregado del mes
  - `obtener_gastos_por_categoria(anio, mes)` — egresos agrupados
- **`generar_alertas()`** (`alertas_service.py`) — detecta 6 tipos de situación (balance negativo, presupuesto agotado, metas próximas a vencer, metas casi completas, cuotas pendientes, sin ahorros) y genera alertas con IA + fallback sin IA
- **`preguntar_a_groq()`** (`groq_client.py`) — tool calling nativo con Groq, modelo `llama-3.3-70b-versatile`, temperatura 0.4

### Frecuencia de alertas

- **Luna de miel:** 3h desde el registro sin alertas (evita conflicto con onboarding)
- **Ventana deslizante:** cada 6h se genera un nuevo lote de alertas

### Frontend

- `agente_financiero.html` — chat completo con burbujas, 4 sugerencias rápidas, indicador de escritura
- `agente_financiero.js` — comunicación vía fetch, formatea respuesta (bold con `**`)
- `agente_financiero.css` — tema premium verde oliva + café
- `alertas_modal.html` — overlay con skeleton loader, sondeo cada 30 min
- Avatar del agente: GASTU (logo `gastu_logo_rostro.png`)

### Tests: 47 tests pytest
### Admin: `MensajeChatAdmin` y `AlertaDiariaAdmin` registrados

---

## 16. App panel_admin — Estado actual (100%)

App `panel_admin` con `namespace='panel_admin'`. Template principal: `panel_admin/templates/panel_admin/base_admin.html`.

- Extiende el mismo layout que `base_app.html` (`static/css/gastuapp_layout.css`) para estandarizar sidebar y topbar.
- Utiliza estilos propios (`panel_admin/static/panel_admin/css/admin.css`) cargados en `extra_head` para tablas, badges, modales y stat cards.
- **Alertas**: Utiliza `GastuAlerts` (`static/js/gastu_alerts.js`) para notificaciones consistentes en toda la aplicación, reemplazando alertas y confirmaciones nativas de JavaScript, lo que soluciona problemas de bloqueo del navegador al cambiar roles o estados.
- **Doble Binding Resuelto**: `admin.js` solo inicializa Lucide y gestiona el toggle de la sidebar. La lógica específica vive en `usuarios.js` y `categorias.js` para evitar múltiples event listeners.

---

## 17. App landing — estado actual (100%)

App `landing` con `namespace='landing'`. Template principal: `landing/templates/landing/home.html`.

- Extiende su propio `landing/base.html` (distinto de `base_app.html`)
- Construida con GSAP + ScrollTrigger, Tailwind CDN, Lucide, Plus Jakarta Sans
- Tema claro con blobs decorativos, animaciones de scroll
- CTA "Ya tengo cuenta" apunta a `{% url 'login' %}`
- Fix aplicado: `body { overflow-x: hidden }` para evitar scroll horizontal por los blobs

---

## 18. Modelo base abstracto

Definida en `movimientos/models.py` como `ModeloBase`. Provee `activo (BooleanField)` y `fecha_creacion (DateTimeField)`.

```python
from movimientos.models import ModeloBase

class NuevoModelo(ModeloBase):
    """Descripción del modelo."""
    ...
```

Todos los modelos nuevos deben heredar de `ModeloBase`. `ahorros/models.py`, `presupuesto/models.py` y `programaciones/models.py` aún no lo hacen (definen sus propios campos `activo` y `fecha_creacion`).

---

## 19. Bugs conocidos y pendientes técnicos

| Archivo | Bug | Estado |
|---|---|---|
| `notificaciones/services.py` | Código duplicado y comentado al final del archivo | Limpieza pendiente |
| `presupuesto/views.py` | Falta `@login_required` | Pendiente |
| `presupuesto/models.py` | Campo `isActivo` en camelCase | Pendiente |
| `presupuesto/api_views.py` | `con_estado` no calcula gastado para inactivos | Pendiente |
| `presupuesto/admin.py` | Modelo no registrado en admin | Pendiente |
| `usuarios/views.py` | Rate limiting en login no implementado | Pendiente |
| `movimientos/views_api.py` | Decidir approach de seguridad para el Agente (CSRF vs Token) | En discusión |

---

## 20. Setup del proyecto desde cero

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

## 21. Convenciones del proyecto

- **Commits:** en español, concisos, con prefijo convencional (`feat:`, `fix:`, `perf:`, `refactor:`)
- **Docstrings:** usar docstrings Python en lugar de comentarios `#` en código de negocio
- **Arquitectura:** FBV (function-based views) — no CBV. Lógica de negocio compleja en `services.py`.
- **Sin emojis** en ningún archivo de código: templates, comentarios, docstrings, variables, strings visibles al usuario. Sin excepciones salvo pedido explícito.
- **CSS:** nunca escribir `{% %}` o `{{ }}` de Django dentro de `style=""` — usar clases CSS predefinidas y aplicar condicionales en `class=""`. Datos para JS via atributos `data-`.
- **Templates:** nunca crear layouts locales por app si ya existe `base_app.html`
- **Separación de archivos:** HTML, CSS y JS en archivos distintos. No mezclar en el template.
- **Seguridad:** toda query filtra por `request.user`. Editar/eliminar siempre con `get_object_or_404(Modelo, pk=pk, usuario=request.user)`.
- **Imports circulares:** resolverlos con import local dentro de la función (patrón usado en signals).
- **Modelos nuevos:** heredar de `ModeloBase`, campos en snake_case, FKs a otras apps con string `'app.Modelo'`, `get_user_model()` en lugar de `User` directo.

---

## 22. Sistema de Historial (Audit Log)

Implementado en la app `historial` para rastrear operaciones CRUD de los usuarios en una ventana de 30 días. La interfaz se basa en un panel Offcanvas renderizado dinámicamente según el módulo.

### Instrucciones para que otras IAs/Devs integren el Historial en sus módulos:

1. **Backend (Signals)**: En tu app (ej. `ahorros/signals.py`), crea signals `post_save` y `post_delete` para registrar la acción.
   ```python
   from historial.models import AccionHistorial
   
   AccionHistorial.objects.create(
       usuario=instance.usuario,
       accion=AccionHistorial.AccionChoices.CREACION, # o EDICION / ELIMINACION
       modulo=AccionHistorial.ModuloChoices.AHORROS,  # Agregar a ModuloChoices si no existe
       descripcion=f"Se registró un ahorro...",
       referencia_id=str(instance.id),
       monto_afectado=instance.monto
   )
   ```
2. **Frontend (Botón)**: En tu template HTML, añade el botón con los atributos `data-tema-*` del color de tu app:
   ```html
   <button class="btn-ghost" type="button" id="btn-historial"
           data-modulo="AHORROS"
           data-tema-accent="#d97706"
           data-tema-light="#fffbeb"
           data-tema-label="Ahorros"
           data-tema-icon="piggy-bank">
     <i data-lucide="history"></i> Historial
   </button>
   ```
3. **Scripts**: Importa el script central en tu template:
   ```html
   <script src="{% static 'historial/js/historial.js' %}"></script>
   ```
El panel se pintará con tus colores y solo listará las acciones de tu `data-modulo`. No agregues emojis por favor.

---

## 23. Sistema de Reportes y Exportación

Implementado a nivel global (principalmente desde la app `dashboard`) para generar documentos consolidados con la imagen corporativa de Gastu.

### Tecnologías Utilizadas
- **Excel (.xlsx)**: Generado mediante `openpyxl`. Genera tablas estilizadas con anchos de columna dinámicos, celdas formateadas como moneda (`#,##0.00`) y colores diferenciados para ingresos (verde) y egresos (rojo).
- **PDF (.pdf)**: Generado mediante `xhtml2pdf`. Utiliza el template HTML `reporte_pdf.html` y lo convierte a PDF. 

### Lineamientos de Identidad Visual (Branding)
- El sistema de reportes PDF incluye cabeceras dinámicas definidas mediante `@page` y `@frame` de xhtml2pdf.
- Los reportes están equipados con la cabecera corporativa de Gastu (logo posicionado a la izquierda, título del proyecto y fecha de generación).
- Todos los recursos estáticos para reportes (logos y banners) se centralizan en la ruta global `static/img/` bajo configuración en `settings.py`. Use nombres como `gastu_logo_rostro.png` o `gastu_grafica.png`.

**Importante:** Cuando se trabaje con templates de renderizado a PDF mediante xhtml2pdf, utilizar estrictamente estilos en línea o bloques `<style>` internos básicos. No usar Tailwind vía CDN porque el motor de PDF no resuelve correctamente utilidades complejas ni variables nativas CSS complejas. Tampoco soporta flexbox/grid. Se debe maquetar usando modelo de cajas tradicional y tablas `<table>`.

---

## 24. Metodología de Pruebas Automatizadas (TDD Visual con Playwright)

GastuApp emplea un flujo de trabajo de pruebas guiado por el comportamiento visual y automatizado por la IA. El proceso para validar un Caso de Uso (CU) consta de los siguientes pasos:

1. **Definición por el Usuario**: El usuario proporciona capturas de pantalla de una matriz de pruebas detallando los "Casos de Prueba" (éxito) y "Casos de Error" esperados para un CU específico.
2. **Preparación de Datos (Seeders)**: El agente IA crea y ejecuta scripts de *seeding* (ej. `tests/seeds/seed_cu21.py`) utilizando el ORM de Django para preparar la base de datos con un estado limpio, predecible y determinista.
3. **Automatización con Playwright**: El agente diseña un script asíncrono en Python usando Playwright (ej. `tests/playwright/take_screenshots_CU21.py`). Este script simula las interacciones exactas del usuario final descritas en la matriz (clicks, navegación, ingresos de texto, flujos de error).
4. **Validación y Fixes (Iteración)**: Si el script encuentra un bug (ej. el sistema no redirige, una alerta no se muestra, o un botón falla), el agente diagnostica el problema, modifica el código fuente (backend o frontend) y re-ejecuta el test hasta que este pase satisfactoriamente.
5. **Evidencia Visual**: Como resultado final, el script toma capturas de pantalla de cada escenario exitoso o fallido y las almacena en una carpeta local `capturas_pruebas/CU-XX/`. (Nota: Estas imágenes y la carpeta se omiten en el control de versiones vía `.gitignore`).

**Directrices para el Agente:**
- Asegurar siempre que los elementos de UI asíncronos (modales, overlays de tour `driver.js`) no bloqueen las interacciones de Playwright. Utilizar `force=True` en los clicks de ser necesario.
- Los scripts de Playwright deben guardarse en `tests/playwright/` y los seeders en `tests/seeds/`.
- **Limpieza del Workspace (Pre-Commit):** ANTES de realizar cualquier commit, el agente DEBE limpiar el entorno de trabajo. Esto incluye:
  - Eliminar por completo la carpeta `capturas_pruebas/` (y su contenido) generada durante las pruebas.
  - Eliminar archivos basura o temporales suministrados por el usuario (ej. `.xlsx`, `.pdf`, `.png` sueltos en la raíz).
  - Eliminar scripts de depuración temporales (`debug_*.py`).
  - Asegurar que `.gitignore` esté actualizado para ignorar estos artefactos de prueba si llegaran a recrearse.

## 25. Pruebas Unitarias con Pytest

El proyecto también incluye pruebas unitarias tradicionales utilizando pytest y pytest-django para validar la lógica de backend y funcionalidades específicas de las aplicaciones.

### Estructura de las pruebas
Las pruebas unitarias se encuentran en cada aplicación en archivos llamados `tests.py` y siguen las convenciones de Django TestCase.

### Ejecutar las pruebas
```bash
# Instalar dependencias de testing (solo primera vez)
pip install pytest pytest-django

# Ejecutar todas las pruebas
pytest

# Ejecutar tests de una app específica
pytest usuarios/tests.py

# Ejecutar tests con cobertura (opcional)
pytest --cov=.
```

### Convenciones de pruebas
- Los tests deben ser exhaustivos pero concisos
- Cada método de prueba debe probar un único concepto
- Utilizar nomes descriptivos para los tests que indiquen claramente qué se está probando
- Los tests deben ser independientes y no depender del estado de otros tests
- Utilizar el método `setUp()` para crear objetos comunes necesarios para múltiples tests

---

## 24. WebSockets y Notificaciones en Tiempo Real

El sistema cuenta con un canal de WebSockets bidireccional gestionado por **Django Channels** y servido mediante **Daphne**. Se utiliza principalmente para "empujar" (push) notificaciones al navegador del usuario sin requerir recargas (polling).

### Arquitectura de WebSockets
1. **Frontend:** `base_app.html` inyecta un listener WebSocket (`ws://` o `wss://`) que escucha eventos tipo `notificacion`.
2. **Backend (Consumers):** `notificaciones/consumers.py` gestiona la conexión asíncrona y la suscripción del usuario a un grupo específico (ej. `notificaciones_{user.id}`).
3. **Dispatchers:** Cuando se crea una notificación (ej. desde `notificaciones/dispatcher.py` en un hilo en segundo plano), el servidor envía un mensaje al *Channel Layer* que luego se retransmite por el túnel WebSocket.
4. **Serialización (JSON):** Todos los valores en el backend (incluidos `Enums` como `Notificacion.Tipo`) deben convertirse explícitamente a `str()` antes de pasar al Channel Layer, ya que un fallo de serialización JSON cerrará silenciosamente la conexión asíncrona.

### Configuración del Channel Layer y Entornos

El sistema soporta dos modos de funcionamiento que se autoconfiguran en `settings.py`:

**1. Desarrollo Local (InMemoryChannelLayer)**
- Activo por defecto cuando NO existe la variable `REDIS_URL`.
- Utiliza la memoria RAM de Python como "tablero de mensajes".
- **Ventaja:** No requiere instalar programas externos (como Redis) en Windows.
- **Limitación:** Solo funciona correctamente dentro del mismo proceso de Python.

**2. Producción / Render (RedisChannelLayer)**
- Activo automáticamente si existe la variable de entorno `REDIS_URL`.
- En producción, con múltiples workers o servidores, el `InMemoryChannelLayer` pierde los mensajes porque no se comparten la memoria.
- **Pasos para desplegar en Render:**
  1. Crear un nuevo servicio **Redis** (plan Free) en la misma región que el Web Service de GastuApp.
  2. Copiar la **Internal URL** provista por Render (ej. `redis://red-...`).
  3. En el Web Service de GastuApp, ir a la sección **Environment** y agregar:
     - `Key`: `REDIS_URL`
     - `Value`: [La Internal URL copiada]
  4. Redesplegar. Django Channels detectará la variable y utilizará Redis como backend de mensajería asíncrona.
