# Plan: captura automatica de movimientos bancarios

> Estado: fase A implementada y probada en local (rama `feat/captura-bancaria`). Falta produccion. Ultima actualizacion: 2026-11-09.

## Objetivo

Que los ingresos y egresos del usuario se registren en Gastu sin entrar a la app, a partir de las alertas por correo que ya envian los bancos. Nunca se piden credenciales bancarias ni acceso a la cuenta de Google del usuario.

## Fases

| Fase | Que es | Cubre |
|---|---|---|
| A | Correo reenviado + bandeja de pendientes | Bancos que envian correo (Android y iPhone) |
| B | Gastu como PWA con Web Push | Avisos en el celular con la app cerrada |
| C | App Android propia (Capacitor) con lector de notificaciones | Nequi y Daviplata (solo Android) |

Descartado: automatizaciones con apps de terceros (MacroDroid, Tasker), porque generan desconfianza en el usuario.

## Fase A

### Flujo

```
Banco -> Gmail del usuario -> filtro de reenvio -> <alias>@<dominio de Gastu>
  -> servidor SMTP propio (aiosmtpd) -> captura_bancaria.services.procesar_correo
  -> parser del banco -> MovimientoDetectado (PENDIENTE)
  -> Notificacion MOVIMIENTO_DETECTADO + push por WebSocket
  -> usuario confirma -> Movimiento -> signals existentes (dashboard, historial, alertas)
```

### Servidor SMTP

- Comando `python manage.py servidor_smtp --port 2525` basado en `aiosmtpd`. Corre dentro del proyecto Django y llama directamente a los servicios (sin salto HTTP).
- En produccion: un servicio mas en `docker-compose.yml` con la misma imagen, puerto 25 de entrada abierto en Oracle.
- Dominio: produccion usa `gastu.duckdns.org`. DuckDNS no permite registros MX; verificar si basta el MX implicito (registro A) o si se necesita otro dominio para el correo. Pendiente antes de produccion.

### App `captura_bancaria`

Modelos:
- `BuzonCaptura`: uno por usuario. Alias secreto, verificado, ultimo correo, regenerable.
- `CorreoEntrante`: remitente, asunto, estado (PROCESADO / IGNORADO / ERROR), texto (se borra a los 30 dias).
- `MovimientoDetectado`: banco, tipo, monto, comercio, fecha de la transaccion, referencia, categoria sugerida, estado (PENDIENTE / CONFIRMADO / DESCARTADO), FK al `Movimiento`, hash unico anti-duplicados.
- `ReglaComercio`: comercio -> categoria aprendida, con `auto_confirmar`.

Servicios:
- `procesar_correo(raw)`: identifica buzon y banco, parsea, crea el detectado.
- `parsers/<banco>.py`: regex por banco; si el formato no se reconoce, se lee con IA (`parsers/ia.py`).
- `parsers/generico.py`: otros bancos colombianos identificados por dominio y leidos con IA.
- `confirmar(detectado, categoria)`: crea el `Movimiento` con `fecha_registro = fecha_transaccion`.
- Deteccion del correo de verificacion de reenvio de Gmail para mostrar el codigo al usuario.

Integraciones:
- `Notificacion.Tipo.MOVIMIENTO_DETECTADO`, push con el dispatcher existente.
- Pagina propia `/captura/` ("Captura automatica" en el menu lateral, seccion Herramientas).
- Bandeja "Pendientes por revisar" con confirmacion en lote.
- Comando `python manage.py simular_correo archivo.eml` para pruebas locales.

### Decisiones tomadas

- Servidor SMTP propio, no servicio externo.
- Desarrollo y pruebas primero 100% en local.
- Egresos detectados que superan el disponible: se registran con advertencia, no se bloquean (el gasto ya ocurrio).

### Seguridad

- Alias secreto y regenerable.
- Verificacion DKIM del dominio del banco (confirmar con correos reales que Gmail la conserva al reenviar).
- Todo entra como pendiente; `auto_confirmar` solo aplica con DKIM valido.

### Insumos pendientes

- Correos reales de Bancolombia en `.eml`, con datos personales tachados: compra con tarjeta, transferencia enviada, transferencia recibida, retiro.

### Pruebas en local

Gmail no puede reenviar a `localhost`, asi que en local:
1. `servidor_smtp` en el puerto 2525 y envio de `.eml` con `smtplib` (prueba el camino SMTP completo).
2. `simular_correo` para iterar rapido sobre parsers.
3. Tests pytest con los `.eml` como fixtures.

## Estado de la implementacion (fase A)

Hecho y probado en local:
- App `captura_bancaria` con los cuatro modelos, admin y migraciones.
- Parser de Bancolombia (compra, transferencia enviada y recibida, pago, retiro, abono) sobre formatos aproximados.
- Sugerencia de categoria: regla aprendida del usuario, luego palabras clave, luego "Otros".
- Antiduplicados por Message-ID y por huella del movimiento.
- Deteccion del codigo de confirmacion de reenvio de Gmail.
- Verificacion DKIM (sin probar con correos reales).
- Servidor SMTP (`servidor_smtp`) que entrega a `/captura/api/ingesta/` con token; rechaza alias inexistentes (550) y otros dominios (no hace relay).
- Pagina `/captura/` (menu lateral: Captura automatica): direccion, guia de Gmail, codigo de verificacion y bandeja de pendientes con confirmacion individual y en lote.
- Notificacion `MOVIMIENTO_DETECTADO` por WebSocket.
- Lectura con IA (Groq) para formatos desconocidos y para Davivienda, BBVA, Nequi, Daviplata y otros 9 bancos. La IA solo extrae: se valida el tipo, la operacion y que el monto aparezca en el texto; todo queda pendiente y se marca "Leido con IA".
- Interfaz renovada: hero con estadisticas, onboarding en 3 pasos, pestanas Por revisar / Historial / Reglas, selector visual de categorias, sellos "Verificado por el banco" y "Leido con IA", checklist de configuracion, guia de Gmail en modal y lista de bancos compatibles.
- Pestana "Por revisar" en el panel de notificaciones con confirmacion de un toque; las notificaciones de movimientos llevan a `/captura/`.
- Reglas con nombre original de la alerta y apodo del destinatario (ej. "Arriendo" para "Transferencia a cuenta *5314"); se pueden precargar antes de que llegue la alerta escribiendo solo la cuenta (*5314), y editar apodo, categoria y registro automatico.
- Direccion de captura oculta por defecto, con boton para revelarla (se oculta sola a los 20 s) y para copiarla.
- Guia de Gmail como asistente de 5 pasos con ilustraciones, codigo de Gmail en vivo y botones para copiar.
- Paleta fucsia propia (antes cian, muy cercana a Programaciones y Perfil).
- Componente compartido `static/css/gastu_hero.css` para la card principal del hero, aplicado en Ingresos, Egresos, Ahorros, Programaciones, Presupuestos y Captura, con una decoracion distinta por vista.
- Prueba de conexion: codigo de un solo uso (30 min) que el usuario se envia desde su correo; Gastu lo detecta, muestra el remitente y cuanto tardo. El filtro de Gmail se confirma aparte con la cabecera X-Forwarded-For de la primera alerta reenviada automaticamente.
- 57 tests en `captura_bancaria/tests/`.

Como probar en local:
1. `python manage.py runserver`
2. `python manage.py servidor_smtp --port 2525`
3. `python manage.py simular_correo captura_bancaria/tests/correos/compra_tarjeta.eml --email <tu email> --smtp`
4. Abrir `/captura/` y confirmar el pendiente.

Pendiente:
- Probado con un correo real de Bancolombia (transferencia enviada, 2026-11-09): parser correcto y firma DKIM valida (`d=ayn.notificacionesbancolombia.com`). Remitente real: `alertasynotificaciones@ayn.notificacionesbancolombia.com`. El original esta en `captura_bancaria/tests/correos_reales/`, ignorado por git.
- Falta: correos reales de compra con tarjeta, transferencia recibida y retiro, y comprobar en produccion que el DKIM sobrevive al reenvio por filtro de Gmail.
- Confirmar con correos reales los dominios de los bancos genericos.
- Produccion: servicio `smtp` en `docker-compose.yml`, puerto 25 abierto en Oracle, `CAPTURA_INGESTA_TOKEN` y `CAPTURA_INGESTA_URL` (red interna, `http://web:8000/captura/api/ingesta/`) en `.env`, y bloquear `/captura/api/ingesta/` en nginx. El dominio no es un bloqueo: DuckDNS publica un MX de `gastu.duckdns.org` que apunta al mismo host (verificado 2026-11-11). Plan completo: `deploy/PLAN_CAPTURA_PRODUCCION.md`.
- Programar `purgar_correos_captura` (borra textos con mas de 30 dias).
- Rate limiting de la ingesta.

Nota de entorno local: si `.env` tiene un `REDIS_URL` que no existe en local (por ejemplo el interno de Render), los avisos por WebSocket fallan tras ~1,4 s de espera de DNS. La ingesta ya no espera por eso, pero las notificaciones en vivo no llegan hasta quitar esa variable en local.
