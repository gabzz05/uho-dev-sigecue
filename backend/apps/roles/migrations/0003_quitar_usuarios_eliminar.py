"""Los usuarios ya no se borran (se desactivan): el permiso usuarios.eliminar sobra."""

from django.db import migrations


def quitar(apps, schema_editor):
    apps.get_model("roles", "Permiso").objects.filter(modulo="usuarios", accion="eliminar").delete()


def restaurar(apps, schema_editor):
    apps.get_model("roles", "Permiso").objects.get_or_create(modulo="usuarios", accion="eliminar")


class Migration(migrations.Migration):
    dependencies = [("roles", "0002_roles_iniciales")]

    operations = [migrations.RunPython(quitar, restaurar)]
