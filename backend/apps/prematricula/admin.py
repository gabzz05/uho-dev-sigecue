from django.contrib import admin

from .models import CampoPrematricula, PeriodoPrematricula, Prematricula


@admin.register(CampoPrematricula)
class CampoPrematriculaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "tipo", "requerido", "orden", "activo"]


@admin.register(PeriodoPrematricula)
class PeriodoPrematriculaAdmin(admin.ModelAdmin):
    list_display = ["otorgamiento", "fecha_inicio", "fecha_cierre"]


@admin.register(Prematricula)
class PrematriculaAdmin(admin.ModelAdmin):
    list_display = ["resultado", "estado", "enviada_at", "fecha_aprobacion"]
    list_filter = ["estado"]
