from django.db import migrations

PLANTILLAS = {'plaza_otorgada': {'asunto': 'SIGECUE — Obtuviste plaza en {{ carrera }}', 'cuerpo': 'Hola, {{ nombre }}:\n\n¡Felicidades! Obtuviste plaza en la carrera {{ carrera }} ({{ entidad }}) para el curso {{ anio }}.\n\nPróximos pasos: entra en SIGECUE y completa la prematrícula, donde se te pedirán los documentos que faltan. Te avisaremos cuando esté disponible y de los plazos para presentarla.\n\nUniversidad de Holguín'}, 'no_seleccionado_segunda': {'asunto': 'SIGECUE — Resultado de tu solicitud de matrícula {{ anio }}', 'cuerpo': 'Hola, {{ nombre }}:\n\nNo obtuviste plaza en esta convocatoria del curso {{ anio }}.\n\nPodrás participar en la segunda convocatoria con las plazas restantes. Te avisaremos cuando se abra.\n\nUniversidad de Holguín'}, 'no_seleccionado_final': {'asunto': 'SIGECUE — Resultado de tu solicitud de matrícula {{ anio }}', 'cuerpo': 'Hola, {{ nombre }}:\n\nNo obtuviste plaza en el curso {{ anio }}. El proceso concluyó para esta convocatoria.\n\nGracias por tu interés en las carreras por encuentro de la Universidad de Holguín.\n\nUniversidad de Holguín'}, 'otorgamiento_para_aprobacion': {'asunto': 'SIGECUE — Otorgamiento {{ anio }} pendiente de aprobación', 'cuerpo': 'Hola, {{ nombre }}:\n\nEl Jefe de la Comisión de Ingreso aprobó el otorgamiento de la {{ convocatoria }} convocatoria del curso {{ anio }}. Revísalo en SIGECUE: al aprobarlo se publica y se avisa a los aspirantes.\n\nUniversidad de Holguín'}}


def crear(apps, schema_editor):
    Plantilla = apps.get_model("configuracion", "PlantillaCorreo")
    for codigo, datos in PLANTILLAS.items():
        Plantilla.objects.get_or_create(codigo=codigo, defaults=datos)


def borrar(apps, schema_editor):
    apps.get_model("configuracion", "PlantillaCorreo").objects.filter(codigo__in=PLANTILLAS).delete()


class Migration(migrations.Migration):
    dependencies = [("configuracion", "0007_plantillas_observaciones")]

    operations = [migrations.RunPython(crear, borrar)]
