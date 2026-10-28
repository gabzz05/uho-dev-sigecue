from django.contrib import admin

from .models import RetencionEjecutada


@admin.register(RetencionEjecutada)
class RetencionEjecutadaAdmin(admin.ModelAdmin):
    list_display = ["fecha", "automatica", "ejecutada_por", "aspirantes_anonimizados", "intereses_anonimizados", "documentos_eliminados"]
