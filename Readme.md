# GastuApp 🟢
Sistema de gestión financiera personal desarrollado como proyecto formativo en el SENA.

> **Stack:** Django 5.2 · PostgreSQL (Supabase) · Django Templates

---

## Requisitos previos
- Python 3.10 o superior *(se recomienda 3.12 — ver nota sobre Python 3.14 abajo)*
- Git

---

## Configuración del entorno local

### 1. Clonar el repositorio
```bash
git clone https://github.com/1Zamuken1/GastuDjango.git
cd GastuDjango
```

### 2. Crear y activar el entorno virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Solicitar el archivo `.env` al líder del equipo por privado y ubicarlo en la raíz del proyecto.

Las variables necesarias son (ver `.env.example`):
```
SECRET_KEY=
DEBUG=
DATABASE_URL=
```

### 5. Aplicar migraciones
```bash
python manage.py migrate
```

### 6. Correr el servidor de desarrollo
```bash
python manage.py runserver
```

La aplicación estará disponible en `http://127.0.0.1:8000`

---

## Estructura del proyecto

```
GastuDjango/
├── gastu_django/        # Configuración central (settings, urls, wsgi)
├── usuarios/            # Módulo de usuarios y preferencias
├── movimientos/         # Módulo de ingresos y egresos
├── ahorros/             # Módulo de metas y aportes de ahorro
├── planificacion/       # Módulo de presupuestos y proyecciones
├── notificaciones/      # Módulo de notificaciones automáticas
├── dashboard/           # Módulo de resumen financiero mensual
├── agente/              # Módulo del agente financiero con IA
├── venv/                # Entorno virtual (no se sube al repo)
├── manage.py
├── requirements.txt
├── .env                 # Variables de entorno (no se sube al repo)
└── .env.example         # Plantilla de variables de entorno
```

---

## Módulos y responsables

| Módulo | Descripción | Modelos principales |
|---|---|---|
| `usuarios` | Registro, login, perfil y preferencias | `Usuario`, `Preferencias` |
| `movimientos` | Registro de ingresos y egresos por categoría | `Movimiento`, `Categoria` |
| `ahorros` | Metas de ahorro y seguimiento de cuotas | `AhorroMeta`, `AporteAhorro` |
| `planificacion` | Presupuestos mensuales y proyecciones recurrentes | `Presupuesto`, `Programacion` |
| `notificaciones` | Alertas automáticas basadas en el comportamiento financiero | `Notificacion` |
| `dashboard` | Resumen financiero mensual acumulado | `ResumenMensual` |
| `agente` | Asistente financiero con IA (Gemini) | `AgenteFinanciero` |

---

## Base de datos
El proyecto usa **PostgreSQL** alojado en **Supabase**.

- Todos los cambios a los modelos se manejan con migraciones de Django.
- Cuando hagas cambios a un modelo, ejecuta:

```bash
python manage.py makemigrations
python manage.py migrate
```

- Commitea siempre el archivo de migración generado para que el resto del equipo pueda aplicarlo.
- Los demás integrantes solo necesitan correr `python manage.py migrate` para sincronizar.

---

## Flujo de trabajo en equipo

1. Antes de empezar a trabajar: `git pull`
2. Si hay migraciones nuevas: `python manage.py migrate`
3. Al terminar cambios a modelos: `python manage.py makemigrations` → commitear el archivo generado
4. Nunca modificar migraciones ya aplicadas en producción

---

## Nota sobre versiones de Python

Este proyecto se está desarrollando con **Python 3.14**. Algunas dependencias como `Pillow` aún no tienen soporte completo para esta versión. Se recomienda usar **Python 3.12** para evitar problemas de compatibilidad.

---

## Variables de entorno

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave secreta de Django |
| `DEBUG` | `True` en desarrollo, `False` en producción |
| `DATABASE_URL` | URL de conexión a Supabase (PostgreSQL) |

---

## Tecnologías principales

| Tecnología | Versión | Uso |
|---|---|---|
| Django | 5.2 | Framework principal |
| psycopg | 3.2.10 | Conector PostgreSQL |
| dj-database-url | 2.3.0 | Parseo de DATABASE_URL |
| python-dotenv | 1.1.0 | Manejo de variables de entorno |
| whitenoise | 6.9.0 | Archivos estáticos en producción |
| google-generativeai | 0.8.5 | Agente financiero con Gemini |
| groq | 0.23.1 | Fallback del agente financiero |