from django.contrib import admin

from .models import Area, Cargo, Carrera, CumFum, Departamento, Facultad, Municipio


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ["nombre", "provincia", "activo"]
    list_filter = ["activo"]


@admin.register(Facultad, CumFum)
class EntidadAdmin(admin.ModelAdmin):
    list_display = ["nombre", "codigo", "municipio", "activo"]
    list_filter = ["activo", "municipio"]
    search_fields = ["nombre", "codigo"]


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "facultad", "cum_fum", "activo"]


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "area", "activo"]


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "activo"]


@admin.register(Carrera)
class CarreraAdmin(admin.ModelAdmin):
    list_display = ["nombre", "codigo", "duracion_anios", "activo"]
    search_fields = ["nombre", "codigo"]
