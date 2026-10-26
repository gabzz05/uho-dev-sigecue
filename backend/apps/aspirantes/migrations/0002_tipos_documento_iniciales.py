"""Documentos que pide RF-046: CI por ambas caras y certificación de estudios."""

from django.db import migrations

TIPOS = [("CI anverso", 1), ("CI reverso", 2), ("Certificación de estudios", 3)]


def crear(apps, schema_editor):
    TipoDocumento = apps.get_model("aspirantes", "TipoDocumento")
    for nombre, orden in TIPOS:
        TipoDocumento.objects.get_or_create(nombre=nombre, defaults={"orden": orden, "obligatorio": True})


def borrar(apps, schema_editor):
    apps.get_model("aspirantes", "TipoDocumento").objects.filter(nombre__in=[n for n, _ in TIPOS]).delete()


class Migration(migrations.Migration):
    dependencies = [("aspirantes", "0001_initial")]

    operations = [migrations.RunPython(crear, borrar)]
