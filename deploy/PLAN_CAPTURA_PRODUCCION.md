# Plan: captura automática en producción

Estado al 2026-11-11: el módulo está en producción pero **apagado**
(`CAPTURA_HABILITADA` no está definido y con `DEBUG=False` queda en `False`).
El código de la captura funciona (probado en local con el servidor SMTP y un correo
real de Bancolombia); falta la infraestructura para recibir correos en Oracle Cloud.

Detalle del módulo y del flujo: [plan_captura_bancaria.md](../plan_captura_bancaria.md).

---

## Dominio: no hace falta uno nuevo

`gastu.duckdns.org` ya sirve para recibir correo (verificado por DNS el 2026-11-11):

| Registro | Valor |
|---|---|
| A | `132.145.189.234` (la VM de Oracle) |
| MX | `gastu.duckdns.org` (DuckDNS lo publica solo, apuntando al mismo host) |

Un correo a `alias@gastu.duckdns.org` llega al puerto 25 de la VM. `gastu.eu.org` no
existe en DNS (la solicitud nunca se aprobó); no es necesario retomarlo. Si más adelante
se quiere un dominio propio, basta con que su proveedor permita crear el registro MX y
cambiar `CAPTURA_DOMINIO`.

---

## Fase 1: código (en el repositorio, probado en Docker local)

1. **Servicio `smtp` en `docker-compose.yml`**
   - Misma imagen que `web`; comando
     `python manage.py servidor_smtp --host 0.0.0.0 --port 2525`.
   - Publicar `25:2525` (el contenedor no necesita root para escuchar).
   - `env_file: .env`, `depends_on: web`, `restart: unless-stopped`.
   - Entrega a `http://web:8000/captura/api/ingesta/` por la red interna de Docker.

2. **TLS en el servidor SMTP (STARTTLS)**
   - Gmail entrega sin cifrar si el servidor no ofrece TLS. Reutilizar el certificado de
     Let's Encrypt que ya usa nginx (`/etc/letsencrypt/live/gastu.duckdns.org/`),
     montado en solo lectura en el contenedor `smtp`.
   - `servidor_smtp` necesita un argumento para el certificado y la llave
     (`aiosmtpd` admite `tls_context`).

3. **Proteger la ingesta en nginx**
   - `location /captura/api/ingesta/ { return 404; }` en el bloque HTTPS: solo el
     contenedor `smtp` la usa, por la red interna.
   - La ingesta ya exige `CAPTURA_INGESTA_TOKEN`; esto es una segunda barrera.

4. **Límite de la ingesta** (pendiente del plan original)
   - Límite por alias y por minuto en `ingesta` (django-ratelimit, como el login), para
     que un remitente no pueda llenar la bandeja de un usuario.

5. **Purga programada de textos**
   - `purgar_correos_captura` borra el texto de los correos con más de 30 días; hoy no
     se ejecuta nunca. Opción simple: un contenedor `cron` o un `cron` del sistema que
     corra `docker compose exec -T web python manage.py purgar_correos_captura` cada día.

6. **(Opcional) Fase piloto: captura solo para algunos usuarios**
   - El interruptor actual es global. Para probar en producción sin mostrársela a todos,
     agregar `CAPTURA_USUARIOS_PILOTO` (lista de correos): con `CAPTURA_HABILITADA=False`,
     esos usuarios igual ven el módulo y su ingesta funciona.

7. **Pruebas**
   - Tests del servicio SMTP con TLS, del bloqueo en nginx (config) y del modo piloto.
   - Prueba en Docker local: `docker compose up` con el servicio `smtp` y envío de un
     `.eml` con `simular_correo --smtp`.

8. **Documentación**
   - Sección nueva en [GUIA_MIGRACION_ORACLE_CLOUD.md](GUIA_MIGRACION_ORACLE_CLOUD.md)
     con el puerto 25 y las variables nuevas; `.env.example` actualizado.

---

## Fase 2: servidor (manual, en Oracle Cloud)

1. **Abrir el puerto 25 de entrada**
   - Consola de OCI: *Networking > Virtual Cloud Networks > [VCN] > Security Lists >
     Default Security List > Add Ingress Rules*: origen `0.0.0.0/0`, TCP, puerto `25`.
   - En la VM:
     ```bash
     sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 25 -j ACCEPT
     sudo netfilter-persistent save || sudo iptables-save | sudo tee /etc/iptables/rules.v4
     ```
   - Oracle bloquea el puerto 25 de **salida**; no afecta, la captura solo recibe.

2. **Variables en `.env`**
   ```env
   CAPTURA_DOMINIO=gastu.duckdns.org
   CAPTURA_INGESTA_URL=http://web:8000/captura/api/ingesta/
   CAPTURA_INGESTA_TOKEN=<valor largo y aleatorio>
   # Fase piloto (opcional): CAPTURA_USUARIOS_PILOTO=tu_correo@gmail.com
   ```
   El token se puede generar en la VM con:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

3. **Desplegar** con el procedimiento de la guía (sección 6): respaldo, `git pull origin main`,
   `docker compose up -d --build`. Comprobar que el contenedor `smtp` está arriba:
   ```bash
   docker compose ps && docker compose logs --tail=30 smtp
   ```

4. **Comprobar el puerto desde fuera** (desde un equipo cuya red no bloquee el 25, o un
   servicio de prueba SMTP): debe responder `220 gastu.duckdns.org`.

---

## Fase 3: prueba real y activación

1. Activar la captura para la cuenta de prueba (modo piloto) o para todos
   (`CAPTURA_HABILITADA=True`) y reiniciar `web`.
2. En Captura automática, activar la dirección y usar **Probar conexión**.
3. En Gmail: *Configuración > Reenvío* con la dirección de captura. El código de
   confirmación que manda Gmail debe aparecer en la página de captura.
4. Crear el filtro de Gmail que reenvía solo los avisos del banco.
5. Hacer una compra o transferencia pequeña y comprobar:
   - que llega el movimiento pendiente y la notificación,
   - que la firma **DKIM** sigue válida tras el reenvío de Gmail (si no, la captura sigue
     funcionando pero nunca se confirma sola),
   - el remitente marcado como del banco.
6. Probar más tipos de correo real: compra con tarjeta, transferencia recibida, retiro.
7. Con todo en orden, `CAPTURA_HABILITADA=True` para todos y quitar el modo piloto.

---

## Riesgos y decisiones abiertas

- **Reputación de DuckDNS:** algunos remitentes podrían tratar distinto un dominio
  gratuito; Gmail entrega a cualquier MX válido, pero conviene confirmarlo en la Fase 3.
- **Spam en el puerto 25:** el servidor rechaza destinatarios de otros dominios y alias
  inexistentes (no hace relay); el límite de la Fase 1 cubre el resto.
- **Privacidad:** el texto de los correos se guarda hasta la purga de 30 días; la purga
  programada debe estar lista antes de abrirla a todos.
