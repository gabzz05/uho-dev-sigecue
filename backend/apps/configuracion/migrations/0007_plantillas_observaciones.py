from django.db import migrations

PLANTILLAS = {
    "solicitud_observada": {'asunto': 'SIGECUE — Hay una observación en tu solicitud de matrícula', 'cuerpo': 'Hola, {{ nombre }}:\n\nAl revisar tu solicitud de matrícula del curso {{ anio }} se hizo una observación sobre: {{ elemento }}.\n\n{{ observacion }}\n\nEntra en SIGECUE, corrígelo en tu perfil y pulsa «Enviar corrección». Mientras la observación no se resuelva, tu solicitud no participa en el otorgamiento de plazas.\n\nUniversidad de Holguín'},
    "observacion_corregida": {'asunto': 'SIGECUE — {{ aspirante }} corrigió lo observado', 'cuerpo': 'Hola, {{ nombre }}:\n\n{{ aspirante }} envió la corrección de: {{ elementos }}.\n\nRevísala en SIGECUE y resuelve o reabre la observación.\n\nUniversidad de Holguín'},
}


def crear(apps, schema_editor):
    Plantilla = apps.get_model("configuracion", "PlantillaCorreo")
    for codigo, datos in PLANTILLAS.items():
        Plantilla.objects.get_or_create(codigo=codigo, defaults=datos)


def borrar(apps, schema_editor):
    apps.get_model("configuracion", "PlantillaCorreo").objects.filter(codigo__in=PLANTILLAS).delete()


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0006_plantilla_solicitud_confirmada")]

    operations = [migrations.RunPython(crear, borrar)]
