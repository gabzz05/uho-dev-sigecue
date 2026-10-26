"""Permiso solicitudes.documentos_descargar: descargar CI, certificación y foto de los aspirantes.

Por semilla solo lo tienen los roles globales y quienes gestionan el ingreso en
la entidad (secretarios y Director(a) de CUM/FUM). Jefes de Área, Vicedecanos y
Admins no: son documentos personales, no información académica resumida.
"""

from django.db import migrations

ROLES = ["jefe_ci", "secretaria_general", "vicerrector", "secretario_facultad", "secretario_cum", "director_cum"]


def crear(apps, schema_editor):
    Permiso = apps.get_model("roles", "Permiso")
    permiso, _ = Permiso.objects.get_or_create(modulo="solicitudes", accion="documentos_descargar")
    for rol in apps.get_model("roles", "Rol").objects.filter(codigo__in=ROLES):
        rol.permisos.add(permiso)


def borrar(apps, schema_editor):
    apps.get_model("roles", "Permiso").objects.filter(modulo="solicitudes", accion="documentos_descargar").delete()


class Migration(migrations.Migration):
    dependencies = [("roles", "0005_jefes_de_area_requieren_area")]

    operations = [migrations.RunPython(crear, borrar)]
