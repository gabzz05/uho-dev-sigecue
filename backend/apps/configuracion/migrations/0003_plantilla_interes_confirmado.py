from django.db import migrations

INTERES = {
    "asunto": "SIGECUE — Registramos tu interés en {{ carrera }}",
    "cuerpo": (
        "Hola, {{ nombre }}:\n\n"
        "Registramos tu interés en la carrera {{ carrera }} ({{ entidad }}) para el curso {{ anio }}.\n\n"
        "Te avisaremos a este correo cuando se abra la convocatoria oficial de solicitud de matrícula.\n\n"
        "Universidad de Holguín"
    ),
}


def crear(apps, schema_editor):
    apps.get_model("configuracion", "PlantillaCorreo").objects.get_or_create(codigo="interes_confirmado", defaults=INTERES)


def borrar(apps, schema_editor):
    apps.get_model("configuracion", "PlantillaCorreo").objects.filter(codigo="interes_confirmado").delete()


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0002_plantilla_activacion")]

    operations = [migrations.RunPython(crear, borrar)]
