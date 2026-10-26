from django.contrib import admin

from .models import EnvioMasivo, Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ["asunto", "usuario", "tipo", "leida", "created_at"]
    list_filter = ["tipo", "leida"]


@admin.register(EnvioMasivo)
class EnvioMasivoAdmin(admin.ModelAdmin):
    list_display = ["asunto", "grupo_descripcion", "destinatarios", "por_correo", "enviado_por", "created_at"]
