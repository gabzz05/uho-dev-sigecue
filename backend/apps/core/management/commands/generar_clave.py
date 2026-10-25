from django.core.management.base import BaseCommand

from apps.core.crypto import generar_clave


class Command(BaseCommand):
    help = "Genera una clave aleatoria de 32 bytes (base64) para FIELD_ENCRYPTION_KEY o SEARCH_HASH_KEY."

    def handle(self, *args, **options):
        self.stdout.write(generar_clave())
