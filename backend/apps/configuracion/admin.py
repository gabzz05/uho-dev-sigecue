from django.contrib import admin

from .models import ConfiguracionSistema, IdentidadVisual, PlantillaCorreo

# El SMTP no se registra en el admin de Django para no exponer la contraseña.
admin.site.register(ConfiguracionSistema)
admin.site.register(IdentidadVisual)


@admin.register(PlantillaCorreo)
class PlantillaCorreoAdmin(admin.ModelAdmin):
    list_display = ["codigo", "asunto", "updated_at"]
