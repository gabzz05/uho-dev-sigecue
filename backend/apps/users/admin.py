from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ["username", "first_name", "last_name", "rol", "is_active"]
    list_filter = ["rol", "is_active", "origen"]
    search_fields = ["username", "first_name", "last_name"]
    fieldsets = UserAdmin.fieldsets + (
        ("SIGECUE", {"fields": ("rol", "origen", "ci", "celular", "foto", "email_verificado", "bloqueado_hasta")}),
    )
