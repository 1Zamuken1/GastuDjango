# AGENT.md — Contexto del proyecto GastuApp

> Documento de referencia para agentes IA y colaboradores.
> Mantener actualizado al final de cada sesión de trabajo significativa.
> Última actualización: 2026-03-25

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
| Base de datos | PostgreSQL vía Supabase (Transaction pooler, puerto 6543) |
| ORM | Django ORM nativo |
| Frontend | Django Templates + Tailwind CDN + ApexCharts + Lucide |
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
├── usuarios/              # Modelo Usuario personalizado, login, register — 70%
├── movimientos/           # Modelo Movimiento — CRUD completo (ingresos y egresos) — 95%
├── categorias/            # Modelo Categoria — CRUD completo (extraída de movimientos) — 100%
├── ahorros/               # Modelo definido, interfaces en progreso — 50%
├── planificacion/         # Sin implementar — otro integrante
├── presupuesto/           # Modelo Presupuesto — otro integrante del equipo
├── notificaciones/        # Modelo Notificacion — lógica de alertas automáticas — 50%
├── dashboard/             # Modelo ResumenMensual — vista principal post-login — 90%
├── agente/                # Sin implementar — integración IA pendiente
├── landing/               # Landing page pública (sin auth) — 100%
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
{% block nav_presupuestos %}{% endblock %}
{% block nav_perfil %}{% endblock %}
{% block nav_categorias %}{% endblock %}
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

### Reglas anti-bugs de Django Templates

- Nunca escribir `{% if %}`, `{{ }}` ni `{%` dentro de comentarios CSS (`/* */`) ni dentro de bloques `<style>` — Django los parsea y lanza `TemplateSyntaxError`.
- Los condicionales Django solo van en atributos `class=""`, nunca en `style=""`.
- Los datos para JavaScript se pasan via atributos `data-` en el HTML. Nunca embeber variables Django directamente en bloques `<script>`.
- Separación estricta: HTML en `.html`, CSS en archivos `.css`, JS en archivos `.js`. No mezclar en el mismo template.

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

## 10. App notificaciones — estado actual (50%)

Servicio `notificaciones/services.py` con función `analizar_movimiento` — disparada por signals de `movimientos`. Crea alertas automáticas en base a reglas (déficit, egreso grande, etc.).

**Modelo `Notificacion`:** campos `titulo`, `tipo` (`DEFICIT`, `EGRESO_GRANDE`, otros), `leida` (Boolean), `fecha_creacion`.

**Bug conocido:** `analizar_movimiento` está definida dos veces en el archivo. La segunda sobreescribe silenciosamente a la primera. Corregir antes de añadir lógica nueva: eliminar la definición de la línea ~29, conservar solo la segunda (la que tiene el parámetro `ultimo_egreso`).

**Pendiente:** interfaz de notificaciones (listado, marcar como leídas). La lógica de creación funciona pero no hay vista dedicada.

---

## 11. App ahorros — estado actual (50%)

Modelo definido pero con deuda técnica. Interfaces en progreso (otro integrante).

**Bug conocido en el modelo:** campos en camelCase (`montoMeta`, `totalAcumulado`, `fechaMeta`, `cantidadCuotas`, `aporteAsignado`, `estadoAp`, `fechaLimite`). Migrar a snake_case al implementar la app.

**Nota de arquitectura:** los ahorros en el dashboard se calculan directamente desde `AporteAhorro` con `fecha_registro__lte=ultimo_dia`. No confiar en `ResumenMensual.total_ahorros` — siempre es 0 porque los signals no están conectados.

---

## 12. App usuarios — estado actual (70%)

### Modelo

Usuario personalizado que extiende `AbstractUser`. Campos adicionales: `telefono` (opcional).

### Form: `UsuarioCreationForm`

Campos: `username`, `email`, `telefono`, `password1`, `password2`.

### Lo que funciona

- Login, registro y logout con vistas propias.
- `register.html` con barra de seguridad de contraseña (4 criterios: longitud, mayúscula, número, especial), toggle de visibilidad, indicador de coincidencia de contraseñas.

### Pendiente (el 30% restante)

- Vista de perfil de usuario (edición de datos, cambio de contraseña).
- Rate limiting en login (`django-ratelimit`).

---

## 13. App presupuesto — estado desconocido

Desarrollada por otro integrante del equipo. URL de lista: `listar_presupuestos` (sin namespace aún).

**Bugs conocidos en el código existente:**
- Ninguna vista tiene `@login_required`.
- Usa `Presupuesto.objects.get(id=id)` sin verificar propietario — cualquier usuario puede editar/eliminar presupuestos ajenos.
- Validación manual con `request.POST` en lugar de `ModelForm`.
- Campo `isActivo` en camelCase en el modelo.
- Template extiende `base.html` legacy en lugar de `base_app.html`.

---

## 14. App agente — sin implementar

Integración con Gemini Flash (Google AI Studio, free tier) — Groq como fallback. Dependencias ya en `requirements.txt`:
- `google-generativeai==0.8.5`
- `groq==0.23.1`

Los endpoints REST de `movimientos/views_api.py` están diseñados para ser consumidos por este agente. Ver sección 8 para la documentación completa de la API.

---

## 15. App landing — estado actual (100%)

App `landing` con `namespace='landing'`. Template principal: `landing/templates/landing/home.html`.

- Extiende su propio `landing/base.html` (distinto de `base_app.html`)
- Construida con GSAP + ScrollTrigger, Tailwind CDN, Lucide, Plus Jakarta Sans
- Tema claro con blobs decorativos, animaciones de scroll
- CTA "Ya tengo cuenta" apunta a `{% url 'login' %}`
- Fix aplicado: `body { overflow-x: hidden }` para evitar scroll horizontal por los blobs

---

## 16. Modelo base abstracto

Definida en `movimientos/models.py` como `ModeloBase`. Provee `activo (BooleanField)` y `fecha_creacion (DateTimeField)`.

```python
from movimientos.models import ModeloBase

class NuevoModelo(ModeloBase):
    """Descripción del modelo."""
    ...
```

Todos los modelos nuevos deben heredar de `ModeloBase`. `ahorros/models.py` y `presupuesto/models.py` aún no lo hacen — corregir al implementar esas apps.

---

## 17. Bugs conocidos y pendientes técnicos

| Archivo | Bug | Estado |
|---|---|---|
| `notificaciones/services.py` | `analizar_movimiento` definida dos veces — la segunda sobreescribe a la primera | Pendiente |
| `presupuesto/views.py` | Ninguna vista tiene `@login_required` | Pendiente |
| `presupuesto/views.py` | `Presupuesto.objects.get(id=id)` sin verificar propietario | Pendiente |
| `presupuesto/views.py` | Validación manual con `request.POST` en lugar de `ModelForm` | Pendiente |
| `presupuesto/templates/presupuesto/listar_presupuestos.html` | Extiende `base.html` legacy | Pendiente |
| `presupuesto/models.py` | Campo `isActivo` en camelCase | Pendiente (con migración) |
| `ahorros/models.py` | Campos en camelCase (`montoMeta`, `totalAcumulado`, etc.) | Pendiente (con migración) |
| `usuarios/views.py` | Rate limiting en login no implementado | Pendiente |
| `movimientos/views_api.py` | Endpoints POST con CSRF habilitado — el agente necesita `@csrf_exempt` o autenticación por token para operar sin sesión HTML previa | Pendiente (decidir approach con el equipo) |

---

## 18. Setup del proyecto desde cero

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

## 19. Convenciones del proyecto

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

## 20. Sistema de Historial (Audit Log)

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

## 21. Sistema de Reportes y Exportación

Implementado a nivel global (principalmente desde la app `dashboard`) para generar documentos consolidados con la imagen corporativa de Gastu.

### Tecnologías Utilizadas
- **Excel (.xlsx)**: Generado mediante `openpyxl`. Genera tablas estilizadas con anchos de columna dinámicos, celdas formateadas como moneda (`#,##0.00`) y colores diferenciados para ingresos (verde) y egresos (rojo).
- **PDF (.pdf)**: Generado mediante `xhtml2pdf`. Utiliza el template HTML `reporte_pdf.html` y lo convierte a PDF. 

### Lineamientos de Identidad Visual (Branding)
- El sistema de reportes PDF incluye cabeceras dinámicas definidas mediante `@page` y `@frame` de xhtml2pdf.
- Los reportes están equipados con la cabecera corporativa de Gastu (logo posicionado a la izquierda, título del proyecto y fecha de generación).
- Todos los recursos estáticos para reportes (logos y banners) se centralizan en la ruta global `static/img/` bajo configuración en `settings.py`. Use nombres como `gastu_logo_rostro.png` o `gastu_grafica.png`.

**Importante:** Cuando se trabaje con templates de renderizado a PDF mediante xhtml2pdf, utilizar estrictamente estilos en línea o bloques `<style>` internos básicos. No usar Tailwind vía CDN porque el motor de PDF no resuelve correctamente utilidades complejas ni variables nativas CSS complejas. Tampoco soporta flexbox/grid. Se debe maquetar usando modelo de cajas tradicional y tablas `<table>`.