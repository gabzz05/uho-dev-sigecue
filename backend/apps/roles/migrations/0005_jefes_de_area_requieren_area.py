from django.db import migrations

JEFES_DE_AREA = ["jefe_area_facultad", "jefe_area_cum"]


def marcar(apps, schema_editor):
    apps.get_model("roles", "Rol").objects.filter(codigo__in=JEFES_DE_AREA).update(requiere_area=True)


def desmarcar(apps, schema_editor):
    apps.get_model("roles", "Rol").objects.filter(codigo__in=JEFES_DE_AREA).update(requiere_area=False)


class Migration(migrations.Migration):
    dependencies = [("roles", "0004_rol_requiere_area")]

    operations = [migrations.RunPython(marcar, desmarcar)]
