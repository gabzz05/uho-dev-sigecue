"""Una observación sobre la certificación de estudios anula el índice validado (decisión del cliente)."""

from django.db import migrations


def marcar(apps, schema_editor):
    apps.get_model("aspirantes", "TipoDocumento").objects.filter(nombre="Certificación de estudios").update(afecta_elegibilidad=True)


def desmarcar(apps, schema_editor):
    apps.get_model("aspirantes", "TipoDocumento").objects.filter(nombre="Certificación de estudios").update(afecta_elegibilidad=False)


class Migration(migrations.Migration):
    dependencies = [("aspirantes", "0003_validacion_indice_y_elegibilidad")]

    operations = [migrations.RunPython(marcar, desmarcar)]
