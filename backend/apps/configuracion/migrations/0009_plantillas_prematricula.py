from django.db import migrations

PLANTILLAS = {'prematricula_abierta': {'asunto': 'SIGECUE — Ya puedes hacer tu prematrícula en {{ carrera }}', 'cuerpo': 'Hola, {{ nombre }}:\n\nYa está abierta la prematrícula de {{ carrera }} ({{ entidad }}). Entra en SIGECUE y completa el formulario: puedes guardarlo y terminarlo en varias sesiones hasta el {{ fecha_cierre }}.\n\nTu carnet de identidad y tu certificación de estudios ya están en tu perfil: no tienes que volver a subirlos.\n\nUniversidad de Holguín'}, 'prematricula_recordatorio': {'asunto': 'SIGECUE — Faltan {{ dias }} día(s) para cerrar tu prematrícula', 'cuerpo': 'Hola, {{ nombre }}:\n\nTu prematrícula de {{ carrera }} ({{ entidad }}) todavía no está completa. El plazo cierra el {{ fecha_cierre }}.\n\nEntra en SIGECUE, entrega lo que falta y envíala.\n\nUniversidad de Holguín'}, 'prematricula_correccion': {'asunto': 'SIGECUE — Hay correcciones en tu prematrícula', 'cuerpo': 'Hola, {{ nombre }}:\n\nAl revisar tu prematrícula de {{ carrera }} ({{ entidad }}) hace falta corregir:\n\n{{ correcciones }}\n\nCorrígelo en SIGECUE y vuelve a enviarla. No pierdes tu plaza.\n\nUniversidad de Holguín'}, 'prematricula_aprobada': {'asunto': 'SIGECUE — Tu prematrícula fue aprobada', 'cuerpo': 'Hola, {{ nombre }}:\n\nTu prematrícula de {{ carrera }} ({{ entidad }}) fue aprobada. La entidad te informará los próximos pasos.\n\nUniversidad de Holguín'}}


def crear(apps, schema_editor):
    Plantilla = apps.get_model("configuracion", "PlantillaCorreo")
    for codigo, datos in PLANTILLAS.items():
        Plantilla.objects.get_or_create(codigo=codigo, defaults=datos)


def borrar(apps, schema_editor):
    apps.get_model("configuracion", "PlantillaCorreo").objects.filter(codigo__in=PLANTILLAS).delete()


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0008_plantillas_otorgamiento")]

    operations = [migrations.RunPython(crear, borrar)]
