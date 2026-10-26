from django.db import migrations

PLANTILLA = {
    "asunto": "SIGECUE — Abrió la convocatoria de matrícula {{ anio }}",
    "cuerpo": (
        "Hola, {{ nombre }}:\n\n"
        "Ya está abierta la convocatoria de solicitud de matrícula en las carreras por encuentro para el curso {{ anio }}. "
        "Puedes presentar tu solicitud hasta el {{ fecha_cierre }}.\n\n"
        "Regístrate o inicia sesión en:\n\n"
        "{{ enlace }}\n\n"
        "Universidad de Holguín"
    ),
}


def crear(apps, schema_editor):
    apps.get_model("configuracion", "PlantillaCorreo").objects.get_or_create(codigo="convocatoria_solicitud_abierta", defaults=PLANTILLA)


def borrar(apps, schema_editor):
    apps.get_model("configuracion", "PlantillaCorreo").objects.filter(codigo="convocatoria_solicitud_abierta").delete()


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0004_plantillas_plan_plazas")]

    operations = [migrations.RunPython(crear, borrar)]
