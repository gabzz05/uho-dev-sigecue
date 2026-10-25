from django.contrib import admin

from .models import Rol


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ["nombre", "codigo", "ambito", "es_sistema", "activo"]
    list_filter = ["ambito", "es_sistema", "activo"]
    filter_horizontal = ["permisos"]
