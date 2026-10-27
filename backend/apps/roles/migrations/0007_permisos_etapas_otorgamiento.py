"""Permisos por etapa del otorgamiento (decisión del cliente sobre RF-058/059 y RF-064).

- generar: Secretaria General, una vez por convocatoria.
- aprobar: Jefe CI, que revisa, ajusta y aprueba.
- publicar: Vicerrector, que revisa, ajusta y, al aprobar, publica.

`otorgamiento.editar` desaparece: quién edita lo decide la etapa.
"""

from django.db import migrations

ASIGNACION = {"generar": ["secretaria_general"], "aprobar": ["jefe_ci"], "publicar": ["vicerrector"]}


def crear(apps, schema_editor):
    Permiso = apps.get_model("roles", "Permiso")
    Rol = apps.get_model("roles", "Rol")
    for accion, roles in ASIGNACION.items():
        permiso, _ = Permiso.objects.get_or_create(modulo="otorgamiento", accion=accion)
        for rol in Rol.objects.filter(codigo__in=roles):
            rol.permisos.add(permiso)
    Permiso.objects.filter(modulo="otorgamiento", accion="editar").delete()


def revertir(apps, schema_editor):
    Permiso = apps.get_model("roles", "Permiso")
    editar, _ = Permiso.objects.get_or_create(modulo="otorgamiento", accion="editar")
    for rol in apps.get_model("roles", "Rol").objects.filter(codigo__in=["jefe_ci", "vicerrector"]):
        rol.permisos.add(editar)
    Permiso.objects.filter(modulo="otorgamiento", accion__in=list(ASIGNACION)).delete()


class Migration(migrations.Migration):
    dependencies = [("roles", "0006_permiso_descargar_documentos")]

    operations = [migrations.RunPython(crear, revertir)]
