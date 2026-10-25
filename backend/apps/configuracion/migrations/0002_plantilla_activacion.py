from django.db import migrations

ACTIVACION = {
    "asunto": "SIGECUE — Activa tu cuenta",
    "cuerpo": (
        "Hola, {{ nombre }}:\n\n"
        "Gracias por registrarte en SIGECUE, el sistema de ingreso a las carreras por encuentro "
        "de la Universidad de Holguín.\n\n"
        "Para activar tu cuenta abre este enlace:\n\n"
        "{{ enlace }}\n\n"
        "El enlace es válido durante {{ horas }} horas. Si no activas la cuenta en ese plazo se "
        "eliminará y tendrás que registrarte de nuevo.\n\n"
        "Si no fuiste tú quien se registró, ignora este mensaje.\n\n"
        "Universidad de Holguín"
    ),
}


def crear(apps, schema_editor):
    apps.get_model("configuracion", "PlantillaCorreo").objects.get_or_create(codigo="activacion_cuenta", defaults=ACTIVACION)


def borrar(apps, schema_editor):
    apps.get_model("configuracion", "PlantillaCorreo").objects.filter(codigo="activacion_cuenta").delete()


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0001_initial")]

    operations = [migrations.RunPython(crear, borrar)]
