from django.db import migrations

PLANTILLA = {
    "asunto": "SIGECUE — Recibimos tu solicitud de matrícula {{ anio }}",
    "cuerpo": (
        "Hola, {{ nombre }}:\n\n"
        "Recibimos tu solicitud de matrícula en la {{ convocatoria }} convocatoria del curso {{ anio }}, "
        "con estas carreras en orden de prioridad:\n\n"
        "{{ carreras }}\n\n"
        "Puedes modificarla en SIGECUE hasta el {{ fecha_cierre }}. Al cierre se congela la última versión.\n\n"
        "Universidad de Holguín"
    ),
}


def crear(apps, schema_editor):
    apps.get_model("configuracion", "PlantillaCorreo").objects.get_or_create(codigo="solicitud_confirmada", defaults=PLANTILLA)


def borrar(apps, schema_editor):
    apps.get_model("configuracion", "PlantillaCorreo").objects.filter(codigo="solicitud_confirmada").delete()


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0005_plantilla_convocatoria_solicitud")]

    operations = [migrations.RunPython(crear, borrar)]
