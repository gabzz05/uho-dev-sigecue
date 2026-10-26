from django.contrib import admin

from .models import DocumentoAspirante, PerfilAspirante, TipoDocumento


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "obligatorio", "activo", "orden"]
    list_filter = ["obligatorio", "activo"]


@admin.register(PerfilAspirante)
class PerfilAspiranteAdmin(admin.ModelAdmin):
    list_display = ["usuario", "indice_declarado", "indice_validado", "perfil_completo"]
    list_filter = ["perfil_completo"]


@admin.register(DocumentoAspirante)
class DocumentoAspiranteAdmin(admin.ModelAdmin):
    list_display = ["perfil", "tipo", "version", "vigente", "formato", "subido_at"]
    list_filter = ["tipo", "vigente"]
