from django.contrib import admin

from .models import Solicitud, SolicitudCarrera


class SolicitudCarreraInline(admin.TabularInline):
    model = SolicitudCarrera
    extra = 0


@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ["aspirante", "convocatoria", "estado", "confirmada_at", "modificada_at"]
    list_filter = ["estado", "convocatoria"]
    inlines = [SolicitudCarreraInline]
