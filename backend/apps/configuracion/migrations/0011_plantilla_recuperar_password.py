from django.db import migrations

RECUPERAR = {
    "asunto": "SIGECUE — Restablece tu contraseña",
    "cuerpo": (
        "Hola, {{ nombre }}:\n\n"
        "Recibimos una solicitud para restablecer la contraseña de tu cuenta en SIGECUE.\n\n"
        "Para elegir una contraseña nueva abre este enlace:\n\n"
        "{{ enlace }}\n\n"
        "El enlace es válido durante {{ horas }} horas y solo se puede usar una vez.\n\n"
        "Si no fuiste tú quien lo pidió, ignora este mensaje: tu contraseña no cambia.\n\n"
        "Universidad de Holguín"
    ),
}


def crear(apps, schema_editor):
    apps.get_model("configuracion", "PlantillaCorreo").objects.get_or_create(codigo="recuperar_password", defaults=RECUPERAR)


def borrar(apps, schema_editor):
    apps.get_model("configuracion", "PlantillaCorreo").objects.filter(codigo="recuperar_password").delete()


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0010_parametros_retencion")]

    operations = [migrations.RunPython(crear, borrar)]
