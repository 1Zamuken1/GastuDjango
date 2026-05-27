# Plan de Implementación: Refactor Arquitectónico del Módulo de Notificaciones

Este plan detalla los pasos para refactorizar y extender el módulo de Notificaciones de `GastuDjango`, alineándolo con la arquitectura empresarial especificada, sin romper funcionalidades existentes en otros módulos.

> **Importante:** Este es un archivo generado a petición tuya en la raíz del proyecto. También he creado un **Artefacto interactivo** (puedes verlo en la UI) con el cual podemos seguir el progreso y donde te dejé un par de preguntas abiertas sobre si deseas agregar Celery ahora o usar `ThreadPoolExecutor`, y sobre cómo manejar las alertas periódicas.

---

### 1. Modelos Core (Notificaciones)
Actualización del modelo base para soportar relaciones genéricas.

- **[MODIFICAR]** `notificaciones/models.py`
  - Agregar `referencia_id` (PositiveIntegerField, nullable).
  - Agregar `referencia_tipo` (CharField, nullable) con opciones: 'movimiento', 'ahorro', 'programacion', 'sistema'.

### 2. Sub-módulo de Preferencias
Implementación del sistema de preferencias granulares por usuario.

- **[NUEVO]** `notificaciones/preferencias/models.py`
  - Crear el modelo `PreferenciasAlertas` con relación `OneToOne` al usuario y los 28 campos de configuración definidos (umbrales, booleanos).
- **[NUEVO]** `notificaciones/preferencias/defaults.py`
  - Definir el `PrefsDTO` (dataclass) y los valores por defecto.
- **[NUEVO]** `notificaciones/preferencias/service.py`
  - Crear `PreferenciasService` con método `obtener(usuario)` (get_or_create) retornando `PrefsDTO`.
- **[MODIFICAR]** `usuarios/views.py` y `perfil.html`
  - Reutilizar la pestaña de preferencias existente en el perfil para conectarla con el nuevo modelo.
- **[NUEVO]** `notificaciones/preferencias/forms.py`
  - Crear `PreferenciasAlertasForm` para procesar el formulario del perfil.
- **[NUEVO]** `notificaciones/preferencias/admin.py`
  - Registrar para panel interno de superusuario (debugging).

### 3. Capa de Análisis y Reglas de Negocio (Checks)
Desacoplamiento de la lógica gigante actual en un patrón Strategy y Contexto.

- **[NUEVO]** `notificaciones/checks/context.py`
  - Definir dataclass `AnalysisContext`.
- **[NUEVO]** `notificaciones/analyzers/base.py`, `egreso.py`, `ingreso.py`
  - Crear el Strategy Pattern.
- **[NUEVO]** `notificaciones/checks/query_helpers.py`
  - Extraer helpers genéricos.
- **[NUEVO]** `notificaciones/checks/egreso_checks.py` e `ingreso_checks.py`
  - Refactorizar las funciones actuales del `services.py` en funciones independientes que reciben un `AnalysisContext` y retornan un request de notificación o None.
- **[ELIMINAR]** `notificaciones/services.py`
  - Se eliminará tras la migración.

### 4. Capa de Coordinación, Persistencia y Tiempo Real (WebSockets)

- **[NUEVO]** `notificaciones/dispatcher.py`
  - Crear `ThreadPoolExecutor` para orquestación asíncrona.
- **[NUEVO]** `notificaciones/factory.py`
  - Crear `NotificationFactory` para manejar la lógica de creación. Enviará mensaje WebSocket al usuario tras crear la notificación.
- **[NUEVO]** `notificaciones/repository.py`
  - Implementar `NotificacionRepository` para aislar consultas DB.
- **[NUEVO]** `notificaciones/consumers.py` y `routing.py`
  - Configurar Django Channels y Redis para enviar notificaciones en tiempo real sin recargar la página (Push model).
- **[MODIFICAR]** `gastu_django/asgi.py` y `settings.py`
  - Setup de channels layers para soportar concurrencia masiva.

### 5. Integración (Señales y Presentación)

- **[MODIFICAR]** `notificaciones/signals.py`
  - Actualizar `post_save` de Movimiento para llamar a `dispatcher.py`. Agregar nuevas señales para `Ahorro` y `Programacion`.
- **[NUEVO]** `notificaciones/context_processors.py`
  - Inyectar `notificaciones_count` globalmente (fix bug de nav-bar en vistas ajenas al dashboard) y registrar en `settings.py`.
- **[MODIFICAR]** `notificaciones/views.py` y `urls.py`
  - Actualizar vistas para que utilicen `NotificacionRepository`.
- **[MODIFICAR]** `notificaciones/apps.py` y `admin.py`
  - `apps.py`: Asegurar que importe señales correctamente al inicio.
  - `admin.py`: Registro interno de modelos para superusuarios.

### 6. Pruebas y QA
- **[NUEVO]** Tests unitarios en `notificaciones/tests/`.
