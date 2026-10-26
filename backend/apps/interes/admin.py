from django.contrib import admin

from .models import ConvocatoriaInteres


@admin.register(ConvocatoriaInteres)
class ConvocatoriaInteresAdmin(admin.ModelAdmin):
    list_display = ["anio_academico", "fecha_inicio", "fecha_cierre", "estado"]
    list_filter = ["estado"]


# Las expresiones de interés no se registran en el admin de Django: contienen
# datos personales y se consultan por la API, que aplica el ámbito de cada rol.
