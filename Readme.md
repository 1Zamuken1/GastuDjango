# GastuApp

Sistema de gestión financiera personal desarrollado como proyecto formativo en SENA (ficha 3065834-1).

---

## Stack técnico

| Capa | Tecnología |
|---|---|
| Backend | Django 5.2 |
| Base de datos | PostgreSQL vía Supabase (Transaction pooler, puerto 6543) |
| ORM | Django ORM nativo |
| Frontend | Django Templates + Tailwind CDN + Lucide Icons |
| Fuentes | Plus Jakarta Sans (display) + DM Sans (cuerpo) |
| Auth | Sistema nativo de Django con vistas propias |
| Exportación | openpyxl (Excel) + reportlab (PDF) + csv stdlib |
| IA / Agente | Gemini Flash (Google AI Studio) — Groq como fallback |
| Driver DB | psycopg[binary]==3.2.10 |
| Python | 3.14 |
| Entorno | Windows, venv en GastuDjango/venv/ |

---

## Setup desde cero

### 1. Clonar el repositorio

```bash
git clone https://github.com/1Zamuken1/GastuDjango.git
cd GastuDjango
```

### 2. Crear y activar entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Solicitar el archivo `.env` al equipo. Nunca está en el repositorio.

Estructura esperada:

```env
SECRET_KEY=django-insecure-cambia-esto
DEBUG=True
DATABASE_URL=postgresql://postgres.<proyecto>:<PASSWORD>@aws-1-sa-east-1.pooler.supabase.com:6543/postgres
```

> Usar puerto **6543** (Transaction pooler), no el 5432.  
> El `DATABASE_URL` debe empezar con `postgresql://`, no `postgres://`.

### 5. Aplicar migraciones

```bash
python manage.py migrate
```

### 6. Ejecutar el servidor

```bash
python manage.py runserver
```

Abrir en el navegador: http://127.0.0.1:8000

---

## Estructura de apps

```
GastuDjango/
├── gastu_django/       # Configuración central (settings, urls, wsgi)
├── usuarios/           # Modelo Usuario personalizado, login, register
├── movimientos/        # Modelo Movimiento — CRUD completo + exportación
├── categorias/         # Modelo Categoria — CRUD completo (solo Admin)
├── notificaciones/     # Alertas automáticas por signals
├── dashboard/          # ResumenMensual — vista principal post-login
├── presupuesto/        # Presupuestos — otro integrante del equipo
├── ahorros/            # Pendiente — otro integrante del equipo
├── planificacion/      # Pendiente — otro integrante del equipo
├── agente/             # Pendiente — integración Gemini Flash
├── landing/            # Landing page pública
└── templates/
    └── base_app.html   # Layout global (todas las vistas app)
```

---

## Módulo de exportación

Los reportes se generan desde las vistas de ingresos y egresos.

Formatos disponibles: **CSV**, **Excel (.xlsx)**, **PDF**

Parámetros aceptados vía GET:

| Parámetro | Descripción |
|---|---|
| `tipo` | `INGRESO`, `EGRESO` o `AMBOS` |
| `fecha_desde` | `YYYY-MM-DD` |
| `fecha_hasta` | `YYYY-MM-DD` |
| `categorias` | IDs separados por coma (vacío = todas) |

---

## Convenciones del proyecto

- **Commits:** en español, con prefijo convencional (`feat:`, `fix:`, `refactor:`, `perf:`, `style:`)
- **Vistas:** FBV únicamente, sin CBV
- **Lógica de negocio:** en `services.py`, no en vistas ni modelos
- **Sin emojis** en código, templates, comentarios ni docstrings
- **CSS/JS:** archivos separados por vista en `static/app/css/` y `static/app/js/`
- **Templates:** siempre extienden `base_app.html`, nunca crean layouts propios

---

## Notas

- `venv/` y `.env` no se suben al repositorio.
- Tailwind se carga vía CDN — no requiere Node.js.
- `openpyxl` y `reportlab` son necesarios para la exportación de reportes.