# Plan de Optimización - GastuApp

> Proyecto: Django 5.2 + DRF 3.17 + Django Templates + Tailwind
> Base de datos: SQLite (dev) / PostgreSQL Supabase (prod)
> Problema: Lentitud general + no soporta >4K usuarios simultáneos

---

## 🔴 CRÍTICO (Producción)

### 1. WhiteNoise no configurado
- **Archivo**: `settings.py`
- **Problema**: `whitenoise` está en requirements pero NO está en `INSTALLED_APPS` ni `MIDDLEWARE`, no hay `STATIC_ROOT`, no hay `STATICFILES_STORAGE`
- **Acción**: Agregar middleware WhiteNoise, definir `STATIC_ROOT`, configurar `STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'`
- **Impacto**: Sin esto, en producción los archivos estáticos (CSS, JS, imágenes) no se sirven correctamente

### 2. Cache sin backend persistente
- **Archivo**: `settings.py`
- **Problema**: No hay configuración `CACHES` → usa cache local-memory (por proceso, se pierde al reiniciar)
- **Acción**: Configurar Redis como backend de cache
- **Dependencia**: Agregar `django-redis` a requirements
- **Impacto**: El dashboard ya usa `cache.get/set` con TTL de 24h pero sin Redis no funciona entre procesos

### 3. Sin índices en la base de datos
- **Archivos**: Todos los `models.py`
- **Problema**: Ningún modelo tiene `db_index=True` en FK, fechas o campos de filtro
- **Modelos críticos**:
  - `Movimiento`: `usuario`, `categoria`, `tipo`, `fecha_registro`
  - `Notificacion`: `usuario`, `leida`, `tipo`
  - `AhorroMeta`: `usuario`, `activo`
  - `ResumenMensual`: `usuario`, `mes`, `anio`
- **Acción**: Agregar `db_index=True` y/o `class Meta: indexes = [...]` en cada modelo
- **Impacto**: Las consultas con filtros por usuario, fecha, tipo se vuelven lentas con pocos registros

---

## 🟠 PRIORIDAD ALTA

### 4. N+1 en notificaciones
- **Archivo**: `notificaciones/services.py:476`
- **Problema**: `Categoria.objects.filter(pk=c_id).values_list(...)` dentro de un loop sobre `recurrentes`
- **Acción**: Hacer un solo query con `__in` para obtener todas las categorías de una vez, o precargar con un diccionario

### 5. `prefetch_related` nunca usado
- **Problema**: Se usa `select_related` en varios lugares pero `prefetch_related` aparece 0 veces en todo el proyecto
- **Acción**: Identificar relaciones inversas (ManyToMany, reverse FK) y agregar `prefetch_related`

### 6. Sin `defer`/`async` en scripts
- **Archivo**: `templates/base_app.html`
- **Problema**: ApexCharts (~500KB), GSAP (~100KB), SweetAlert2 (~40KB), Driver.js (~50KB), Lucide (~30KB) se cargan sin `defer` ni `async` → bloquean el renderizado
- **Acción**: Agregar `defer` a scripts no críticos, cargar ApexCharts y GSAP al final del `<body>`

### 7. JS sin minificar ni empaquetar
- **Problema**: `dashboard.js` (861 lines), `movimientos_base.js` (554 lines), `gastuapp_layout.js` (211 lines) — código development sin minificar
- **Acción**: Configurar bundler (Vite) o al menos minificar manualmente; o usar `django-compressor`

---

## 🟡 PRIORIDAD MEDIA

### 8. Sin WebP ni lazy loading en imágenes
- **Archivos**: `static/img/` (6 imágenes PNG/JPG), `templates/base_app.html:166`
- **Problema**: Imágenes en PNG/JPG sin compresión moderna; `loading="lazy"` ausente
- **Acción**: Convertir a WebP, agregar `loading="lazy"` y `width`/`height` a todas las `<img>`

### 9. Sin configuración de producción
- **`.env`**: `DEBUG=True` por defecto, `SECRET_KEY` hardcodeada
- **Problema**: Sin Docker, sin `STATIC_ROOT`, sin configuración production-ready
- **Acción**: Crear Dockerfile/docker-compose, separar settings por entorno (dev/prod)

### 10. Sin headers de cache en respuestas
- **Problema**: No hay `Cache-Control`, `ETag`, `Expires` en ninguna vista
- **Acción**: Usar `django.middleware.cache.UpdateCacheMiddleware` y `FetchFromCacheMiddleware`, o agregar `@cache_control` en vistas

### 11. N+1 en ahorros
- **Archivo**: `ahorros/views.py:34-45`
- **Problema**: `AhorroMeta.objects.filter(usuario=request.user)` sin `select_related('categoria')` — cada acceso a categoría genera query extra
- **Acción**: Agregar `.select_related('categoria')`

### 12. Skeleton loaders solo en un lugar
- **Problema**: Solo existe en `alertas_modal.html`, el resto usa texto "Cargando..."
- **Acción**: Implementar skeleton loaders en dashboard, movimientos y paneles principales

---

## 🟢 PRIORIDAD BAJA

### 13. Duplicación de lógica de agregación
- **Archivos**: `dashboard/services.py:41-60` y `notificaciones/services.py`
- **Acción**: Crear un service/repo compartido para cálculos de total_ingresos/total_egresos

### 14. Sin herramientas de profiling
- **Problema**: No hay `django-silk`, `django-debug-toolbar` ni `nplusone` detector
- **Acción**: Agregar `django-debug-toolbar` en dev, `django-silk` para profiling

### 15. Sin CDN
- **Problema**: Todos los assets estáticos servidos desde Django directamente
- **Acción**: Configurar Cloudflare o similar para cachear assets

---

## ORDEN DE EJECUCIÓN RECOMENDADO

| Orden | Tarea | Esfuerzo | Impacto |
|-------|-------|----------|---------|
| 1 | Configurar WhiteNoise (#1) | Bajo | 🔴 Crítico |
| 2 | Agregar índices SQL (#3) | Medio | 🔴 Crítico |
| 3 | Configurar Redis + cache (#2) | Medio | 🔴 Crítico |
| 4 | Fix N+1 notificaciones (#4) | Bajo | 🟠 Alto |
| 5 | Fix N+1 ahorros (#11) | Bajo | 🟠 Alto |
| 6 | Agregar `defer` a scripts (#6) | Bajo | 🟠 Alto |
| 7 | WebP + lazy loading (#8) | Bajo | 🟡 Medio |
| 8 | Minificar JS / django-compressor (#7) | Medio | 🟡 Medio |
| 9 | Cache headers (#10) | Bajo | 🟡 Medio |
| 10 | Skeleton loaders (#12) | Medio | 🟡 Medio |
| 11 | Separar settings producción (#9) | Medio | 🟡 Medio |
| 12 | `prefetch_related` faltantes (#5) | Medio | 🟠 Alto |
| 13 | Refactor duplicación (#13) | Medio | 🟢 Bajo |
| 14 | Profiling tools (#14) | Bajo | 🟢 Bajo |
| 15 | CDN (#15) | Bajo | 🟢 Bajo |

---

## COMANDOS ÚTILES

```bash
# Agregar dependencias
pip install django-redis whitenoise django-compressor django-debug-toolbar django-silk

# Colectar estáticos (después de configurar WhiteNoise)
python manage.py collectstatic

# Generar migraciones con índices
python manage.py makemigrations
python manage.py migrate

# Ver queries SQL en consola
python manage.py shell -c "from django.db import connection; connection.queries"
```
