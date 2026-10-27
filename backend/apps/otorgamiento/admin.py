from django.contrib import admin

from .models import AjusteOtorgamiento, Otorgamiento, ResultadoOtorgamiento


@admin.register(Otorgamiento)
class OtorgamientoAdmin(admin.ModelAdmin):
    list_display = ["convocatoria", "estado", "generado_at", "publicado_at"]
    list_filter = ["estado"]


@admin.register(ResultadoOtorgamiento)
class ResultadoOtorgamientoAdmin(admin.ModelAdmin):
    list_display = ["otorgamiento", "posicion_ranking", "aspirante_nombre", "indice_utilizado", "carrera", "entidad", "tipo"]
    list_filter = ["otorgamiento", "tipo"]
    search_fields = ["aspirante_nombre"]


@admin.register(AjusteOtorgamiento)
class AjusteOtorgamientoAdmin(admin.ModelAdmin):
    list_display = ["otorgamiento", "resultado", "tipo", "usuario", "created_at", "activo"]
    list_filter = ["tipo", "activo"]
