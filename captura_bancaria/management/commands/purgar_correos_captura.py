from django.core.management.base import BaseCommand

from captura_bancaria.services import purgar_textos_antiguos


class Command(BaseCommand):
    help = 'Borra el texto de los correos de captura con mas de N dias (por defecto 30).'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=30)

    def handle(self, *args, **opts):
        total = purgar_textos_antiguos(opts['dias'])
        self.stdout.write(self.style.SUCCESS(f'Textos borrados: {total}'))
