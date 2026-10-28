"""Campos de RF-065 que no están en el perfil. La foto tipo carné es distinta de la foto de perfil (decisión del cliente)."""

from django.db import migrations

CAMPOS = [
    ("Foto tipo carné", "imagen", 1),
    ("Carta de autorización del centro de trabajo", "archivo", 2),
    ("Solicitud personal firmada", "archivo", 3),
]


def crear(apps, schema_editor):
    Campo = apps.get_model("prematricula", "CampoPrematricula")
    for nombre, tipo, orden in CAMPOS:
        Campo.objects.get_or_create(nombre=nombre, defaults={"tipo": tipo, "orden": orden, "requerido": True})


def borrar(apps, schema_editor):
    apps.get_model("prematricula", "CampoPrematricula").objects.filter(nombre__in=[c[0] for c in CAMPOS]).delete()


class Migration(migrations.Migration):
    dependencies = [("prematricula", "0001_initial")]

    operations = [migrations.RunPython(crear, borrar)]
