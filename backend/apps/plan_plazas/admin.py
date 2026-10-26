from django.contrib import admin

from .models import PlanPlazas


@admin.register(PlanPlazas)
class PlanPlazasAdmin(admin.ModelAdmin):
    list_display = ["anio_academico", "complementaria_de", "estado", "version", "fecha_aprobacion"]
    list_filter = ["estado"]
    # El flujo se gestiona solo por la API: aquí es de consulta.
    readonly_fields = [f.name for f in PlanPlazas._meta.fields]
