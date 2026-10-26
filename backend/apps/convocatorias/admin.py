from django.contrib import admin

from .models import ConvocatoriaSolicitud


@admin.register(ConvocatoriaSolicitud)
class ConvocatoriaSolicitudAdmin(admin.ModelAdmin):
    list_display = ["anio_academico", "numero", "fecha_inicio", "fecha_cierre", "estado"]
    list_filter = ["estado"]
