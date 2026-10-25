"""Precarga los 14 municipios de la provincia de Holguín."""

from django.db import migrations

MUNICIPIOS = [
    "Antilla", "Báguanos", "Banes", "Cacocum", "Calixto García", "Cueto", "Frank País",
    "Gibara", "Holguín", "Mayarí", "Moa", "Rafael Freyre", "Sagua de Tánamo", "Urbano Noris",
]


def cargar(apps, schema_editor):
    Municipio = apps.get_model("nomencladores", "Municipio")
    for nombre in MUNICIPIOS:
        Municipio.objects.get_or_create(nombre=nombre, provincia="Holguín")


def descargar(apps, schema_editor):
    apps.get_model("nomencladores", "Municipio").objects.filter(nombre__in=MUNICIPIOS, provincia="Holguín").delete()


class Migration(migrations.Migration):
    dependencies = [("nomencladores", "0001_initial")]

    operations = [migrations.RunPython(cargar, descargar)]
