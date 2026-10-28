"""Prematrícula: la Secretaría General configura el período y los roles globales también revisan.

- prematricula.configurar: Secretaría General.
- prematricula.editar (revisar): además de Admin y Secretario de cada entidad, Jefe CI y Secretaría General.
"""

from django.db import migrations

ASIGNACION = {"configurar": ["secretaria_general"], "editar": ["jefe_ci", "secretaria_general"]}


def crear(apps, schema_editor):
    Permiso = apps.get_model("roles", "Permiso")
    Rol = apps.get_model("roles", "Rol")
    for accion, roles in ASIGNACION.items():
        permiso, _ = Permiso.objects.get_or_create(modulo="prematricula", accion=accion)
        for rol in Rol.objects.filter(codigo__in=roles):
            rol.permisos.add(permiso)


def revertir(apps, schema_editor):
    Permiso = apps.get_model("roles", "Permiso")
    Rol = apps.get_model("roles", "Rol")
    editar = Permiso.objects.filter(modulo="prematricula", accion="editar").first()
    if editar:
        for rol in Rol.objects.filter(codigo__in=ASIGNACION["editar"]):
            rol.permisos.remove(editar)
    Permiso.objects.filter(modulo="prematricula", accion="configurar").delete()


class Migration(migrations.Migration):
    dependencies = [("roles", "0007_permisos_etapas_otorgamiento")]

    operations = [migrations.RunPython(crear, revertir)]
