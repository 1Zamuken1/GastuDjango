# GastuApp

Sistema de gestión financiera personal desarrollado como proyecto formativo en SENA (ficha 3065834-1).

---

## Stack técnico

| Capa | Tecnología |
|---|---|
| Backend | Django 5.2 |
| Base de datos | SQLite (desarrollo) / PostgreSQL vía Supabase (producción) |
| ORM | Django ORM nativo |
| Frontend | Django Templates + Tailwind CDN + Lucide Icons |
| Fuentes | Plus Jakarta Sans (display) + DM Sans (cuerpo) |
| Auth | Sistema nativo de Django con vistas propias |
| Exportación | openpyxl (Excel) + reportlab (PDF) + csv stdlib |
| IA / Agente | Gemini Flash (Google AI Studio) — Groq como fallback |
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

Crear un archivo `.env` en la raíz del proyecto con el siguiente contenido:

```env
SECRET_KEY=django-insecure-sr^8%d0t&zht-2qbvnql&_p0a0(qd6b2v*@9u#z^6-u(zbrjul
DEBUG=True

# Cambiar a False para usar Supabase
USE_SQLITE=True

# Solo necesario cuando USE_SQLITE=False
# DATABASE_URL=postgresql://postgres.<proyecto>:<PASSWORD>@aws-1-sa-east-1.pooler.supabase.com:6543/postgres
```

### 5. Aplicar migraciones

```bash
python manage.py migrate
```

> Cada miembro del equipo debe correr este comando en su propia máquina.
> El archivo `db.sqlite3` es local y no se sube al repositorio.

### 6. Crear superusuario (para acceder al admin y gestionar categorías)

```bash
python manage.py createsuperuser
```

### 7. Cargar categorías iniciales

```bash
python manage.py loaddata categorias_iniciales
```

Carga 26 categorías predefinidas: 10 de ingresos, 10 de egresos y 6 de ahorros.
Solo es necesario correrlo una vez por máquina, después del `migrate`.

### 8. Ejecutar el servidor

```bash
python manage.py runserver
```

Abrir en el navegador: http://127.0.0.1:8000

---

## Switch de base de datos

El proyecto soporta dos modos sin modificar código:

| `USE_SQLITE` en `.env` | Base de datos activa |
|---|---|
| `True` | SQLite local — carga instantánea, ideal para desarrollo |
| `False` o no definido | Supabase / PostgreSQL — para producción |

Para volver a Supabase: cambiar `USE_SQLITE=False` en `.env` y asegurarse de que `DATABASE_URL` esté definido.

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

- `venv/`, `.env` y `db.sqlite3` no se suben al repositorio.
- Tailwind se carga vía CDN — no requiere Node.js.
- `openpyxl` y `reportlab` son necesarios para la exportación de reportes.
- En producción con Railway/Render: cambiar `USE_SQLITE=False` y configurar `DATABASE_URL`.