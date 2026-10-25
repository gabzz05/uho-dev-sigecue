from django.contrib import admin

from .models import LogAuditoria


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ["created_at", "usuario_nombre", "accion", "modulo", "ip", "resultado"]
    list_filter = ["resultado", "modulo"]
    search_fields = ["usuario_nombre", "accion"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
