"""
Simula la llegada de un correo bancario a un buzon de captura.

Ejemplos:
  python manage.py simular_correo correo.eml --email usuario@ejemplo.com
  python manage.py simular_correo correo.eml --email usuario@ejemplo.com --smtp
  python manage.py simular_correo --texto "Bancolombia: Compraste $45.000 en EXITO..." --email u@e.com

Sin --smtp procesa el correo directamente (rapido para iterar parsers).
Con --smtp lo envia al servidor SMTP local, probando el camino completo.
"""
import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from captura_bancaria.models import BuzonCaptura
from captura_bancaria.services import procesar_correo


class Command(BaseCommand):
    help = 'Envia un correo .eml (o un texto) al buzon de captura de un usuario.'

    def add_arguments(self, parser):
        parser.add_argument('archivo', nargs='?', help='Ruta a un archivo .eml')
        parser.add_argument('--email', required=True, help='Email del usuario destino')
        parser.add_argument('--texto', help='Cuerpo de la alerta, en lugar de un .eml')
        parser.add_argument('--remitente', default='alertasynotificaciones@bancolombia.com.co')
        parser.add_argument('--asunto', default='Alertas y Notificaciones')
        parser.add_argument('--smtp', action='store_true', help='Enviar por el servidor SMTP local')
        parser.add_argument('--smtp-host', default='127.0.0.1')
        parser.add_argument('--smtp-port', type=int, default=2525)

    def handle(self, *args, **opts):
        usuario = get_user_model().objects.filter(email=opts['email']).first()
        if usuario is None:
            raise CommandError(f'No existe un usuario con email {opts["email"]}')
        buzon, creado = BuzonCaptura.objects.get_or_create(usuario=usuario)
        if creado:
            self.stdout.write(f'Buzon creado: {buzon.direccion}')

        raw = self._construir(opts)

        if opts['smtp']:
            with smtplib.SMTP(opts['smtp_host'], opts['smtp_port'], timeout=30) as smtp:
                smtp.sendmail(opts['remitente'], [buzon.direccion], raw)
            self.stdout.write(self.style.SUCCESS(f'Enviado por SMTP a {buzon.direccion}'))
            return

        resultado, detectado = procesar_correo(raw, buzon.direccion)
        self.stdout.write(self.style.SUCCESS(f'Resultado: {resultado}'))
        if detectado:
            cat = detectado.categoria_sugerida.nombre if detectado.categoria_sugerida else '-'
            self.stdout.write(
                f'  {detectado.tipo} {detectado.operacion} ${detectado.monto} | {detectado.comercio} | '
                f'{detectado.fecha_transaccion:%Y-%m-%d %H:%M} | {detectado.producto or "-"} | categoria: {cat}'
            )

    def _construir(self, opts):
        if opts['archivo']:
            ruta = Path(opts['archivo'])
            if not ruta.exists():
                raise CommandError(f'No existe el archivo {ruta}')
            return ruta.read_bytes()
        if not opts['texto']:
            raise CommandError('Indica un archivo .eml o --texto')
        msg = EmailMessage()
        msg['From'] = opts['remitente']
        msg['To'] = f'usuario@{settings.CAPTURA_DOMINIO}'
        msg['Subject'] = opts['asunto']
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain='simulado.local')
        msg.set_content(opts['texto'])
        return msg.as_bytes()
