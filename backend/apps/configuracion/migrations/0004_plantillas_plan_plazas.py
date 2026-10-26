from django.db import migrations

PLANTILLAS_PLAN = {
    "plan_enviado": {
        "asunto": "SIGECUE — Plan de plazas {{ anio }} para revisión",
        "cuerpo": (
            "Hola, {{ nombre }}:\n\n"
            "La Comisión de Ingreso envió la propuesta del plan de plazas {{ anio }} para {{ entidad }}.\n\n"
            "Revísala en SIGECUE: puedes aceptarla, ajustar las cantidades, pedir quitar carreras o agregar otras, "
            "justificando cada cambio. Luego envía la propuesta de tu entidad.\n\n"
            "Universidad de Holguín"
        ),
    },
    "plan_para_aprobacion": {
        "asunto": "SIGECUE — Plan de plazas {{ anio }} pendiente de aprobación",
        "cuerpo": (
            "Hola, {{ nombre }}:\n\n"
            "La Comisión de Ingreso generó la versión {{ version }} del plan de plazas {{ anio }} y está pendiente de tu aprobación.\n\n"
            "Universidad de Holguín"
        ),
    },
    "plan_devuelto": {
        "asunto": "SIGECUE — Plan de plazas {{ anio }} devuelto con observaciones",
        "cuerpo": (
            "Hola, {{ nombre }}:\n\n"
            "El Vicerrector devolvió el plan de plazas {{ anio }} con estas observaciones:\n\n"
            "{{ observaciones }}\n\n"
            "Universidad de Holguín"
        ),
    },
    "plan_publicado": {
        "asunto": "SIGECUE — Plan de plazas {{ anio }} aprobado y publicado",
        "cuerpo": (
            "Hola, {{ nombre }}:\n\n"
            "El Vicerrector de Formación aprobó el plan de plazas {{ anio }}. Ya puedes consultarlo en SIGECUE.\n\n"
            "Universidad de Holguín"
        ),
    },
}


def crear(apps, schema_editor):
    PlantillaCorreo = apps.get_model("configuracion", "PlantillaCorreo")
    for codigo, datos in PLANTILLAS_PLAN.items():
        PlantillaCorreo.objects.get_or_create(codigo=codigo, defaults=datos)


def borrar(apps, schema_editor):
    apps.get_model("configuracion", "PlantillaCorreo").objects.filter(codigo__in=PLANTILLAS_PLAN).delete()


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0003_plantilla_interes_confirmado")]

    operations = [migrations.RunPython(crear, borrar)]
