"""
Servidor SMTP de captura bancaria.

Recibe los correos reenviados por los usuarios y los entrega a la ingesta de Django
(CAPTURA_INGESTA_URL) por HTTP interno. Asi el procesamiento ocurre en el proceso
web, que es el que tiene abiertos los WebSockets de notificaciones.

Uso local:      python manage.py servidor_smtp --port 2525
Uso produccion: python manage.py servidor_smtp --host 0.0.0.0 --port 25
"""
import asyncio
import logging
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

MAX_BYTES = 5 * 1024 * 1024


class CapturaHandler:
    """Handler de aiosmtpd: valida destinatarios y reenvia el correo a la ingesta."""

    def __init__(self, dominio, url, token, stdout):
        self.dominio = dominio.lower()
        self.url = url
        self.token = token
        self.stdout = stdout

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        """Rechaza destinatarios de otros dominios: este servidor nunca hace relay."""
        dominio = address.rsplit('@', 1)[-1].lower() if '@' in address else ''
        if dominio != self.dominio:
            return '550 5.1.1 Destinatario no aceptado'
        envelope.rcpt_tos.append(address)
        return '250 OK'

    async def handle_DATA(self, server, session, envelope):
        raw = envelope.original_content or envelope.content
        if isinstance(raw, str):
            raw = raw.encode('utf-8')
        if len(raw) > MAX_BYTES:
            return '552 5.3.4 Mensaje demasiado grande'

        respuestas = []
        for destinatario in envelope.rcpt_tos:
            respuestas.append(await asyncio.to_thread(self._entregar, raw, destinatario))

        if any(r == 200 for r in respuestas):
            return '250 OK'
        if all(r == 404 for r in respuestas):
            return '550 5.1.1 Buzon no existe'
        return '451 4.3.0 Error temporal, intente mas tarde'

    def _entregar(self, raw, destinatario):
        inicio = time.monotonic()
        try:
            resp = requests.post(
                self.url, data=raw, timeout=30,
                headers={
                    'X-Captura-Token': self.token,
                    'X-Captura-Destinatario': destinatario,
                    'Content-Type': 'message/rfc822',
                },
            )
            estado = resp.status_code
            detalle = resp.json().get('resultado', '') if resp.headers.get('Content-Type', '').startswith('application/json') else ''
        except requests.RequestException as exc:
            estado, detalle = 0, str(exc)
        ms = int((time.monotonic() - inicio) * 1000)
        self.stdout.write(f'[smtp] {destinatario} -> HTTP {estado} {detalle} ({ms} ms)')
        return estado


class Command(BaseCommand):
    help = 'Inicia el servidor SMTP que recibe las alertas bancarias reenviadas.'

    def add_arguments(self, parser):
        parser.add_argument('--host', default='127.0.0.1')
        parser.add_argument('--port', type=int, default=2525)

    def handle(self, *args, **opts):
        from aiosmtpd.controller import Controller

        token = settings.CAPTURA_INGESTA_TOKEN
        if not token:
            self.stderr.write('CAPTURA_INGESTA_TOKEN no esta configurado.')
            return

        handler = CapturaHandler(settings.CAPTURA_DOMINIO, settings.CAPTURA_INGESTA_URL, token, self.stdout)
        controller = Controller(
            handler, hostname=opts['host'], port=opts['port'],
            data_size_limit=MAX_BYTES, server_hostname=settings.CAPTURA_DOMINIO,
        )
        controller.start()
        self.stdout.write(
            f'Servidor SMTP de captura en {opts["host"]}:{opts["port"]} '
            f'para *@{settings.CAPTURA_DOMINIO} -> {settings.CAPTURA_INGESTA_URL}'
        )
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
        finally:
            controller.stop()
