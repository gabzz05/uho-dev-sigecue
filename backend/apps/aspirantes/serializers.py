from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.validators import MAX_ARCHIVO_MB, formato_documento

from . import services
from .models import MAX_TOTAL_MB, MAX_VERSIONES, DocumentoAspirante, PerfilAspirante, TipoDocumento


class TipoDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoDocumento
        fields = ["id", "nombre", "obligatorio", "afecta_elegibilidad", "activo", "orden"]


class DocumentoSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source="tipo.nombre", read_only=True)
    archivo = serializers.SerializerMethodField(help_text="Ruta de la API para descargarlo (requiere el token).")

    class Meta:
        model = DocumentoAspirante
        fields = ["id", "tipo", "tipo_nombre", "version", "vigente", "nombre_original", "formato", "tamano", "subido_at", "archivo"]

    def get_archivo(self, documento) -> str:
        return f"/documentos/{documento.pk}/archivo/"


class PerfilAspiranteSerializer(serializers.ModelSerializer):
    """Perfil del aspirante con lo que le falta para completarlo (RF-046)."""

    nombre = serializers.CharField(source="usuario.first_name", read_only=True)
    apellidos = serializers.CharField(source="usuario.last_name", read_only=True)
    ci = serializers.CharField(source="usuario.ci", read_only=True)
    email = serializers.CharField(source="usuario.email", read_only=True)
    celular = serializers.CharField(source="usuario.celular", read_only=True)
    tiene_foto = serializers.SerializerMethodField()
    perfil_completo = serializers.SerializerMethodField()
    requisitos = serializers.SerializerMethodField()
    bloqueado = serializers.SerializerMethodField()
    documentos = serializers.SerializerMethodField()
    limites = serializers.SerializerMethodField()
    a_corregir = serializers.SerializerMethodField()

    class Meta:
        model = PerfilAspirante
        fields = [
            "nombre", "apellidos", "ci", "email", "celular", "tiene_foto", "centro_trabajo",
            "indice_declarado", "indice_validado", "perfil_completo", "requisitos", "bloqueado", "documentos", "limites",
            "a_corregir",
        ]
        read_only_fields = ["indice_validado"]
        extra_kwargs = {"indice_declarado": {"coerce_to_string": False}, "indice_validado": {"coerce_to_string": False}}

    def _requisitos(self, perfil):
        if not hasattr(perfil, "_requisitos"):
            perfil._requisitos = services.requisitos_perfil(perfil)
        return perfil._requisitos

    def get_tiene_foto(self, perfil) -> bool:
        return bool(perfil.usuario.foto)

    def get_perfil_completo(self, perfil) -> bool:
        return services.calcular_perfil_completo(perfil, self._requisitos(perfil))

    @extend_schema_field(
        serializers.ListField(
            child=serializers.DictField(), help_text="[{clave, nombre, cumple}] en orden; `listo_para_carreras` va aparte."
        )
    )
    def get_requisitos(self, perfil):
        requisitos = self._requisitos(perfil)
        return [{"clave": clave, "nombre": nombre, "cumple": requisitos[clave]} for clave, nombre in services.REQUISITOS.items()]

    def get_bloqueado(self, perfil) -> bool:
        return services.perfil_bloqueado(perfil.usuario)

    @extend_schema_field(serializers.ListField(child=serializers.DictField(), help_text="[{tipo, documento|null}] por tipo activo."))
    def get_documentos(self, perfil):
        vigentes = {d.tipo_id: d for d in perfil.documentos.filter(vigente=True).select_related("tipo")}
        return [
            {
                "tipo": TipoDocumentoSerializer(tipo).data,
                "documento": DocumentoSerializer(vigentes[tipo.pk]).data if tipo.pk in vigentes else None,
            }
            for tipo in TipoDocumento.objects.filter(activo=True)
        ]

    @extend_schema_field(
        serializers.ListField(child=serializers.DictField(), help_text="[{objetivo, tipo_documento}] con observaciones por corregir.")
    )
    def get_a_corregir(self, perfil):
        from apps.solicitudes.revision import objetivos_a_corregir

        return [{"objetivo": o, "tipo_documento": t} for o, t in sorted(objetivos_a_corregir(perfil.usuario), key=str)]

    @extend_schema_field(serializers.DictField())
    def get_limites(self, perfil):
        return {
            "listo_para_carreras": services.listo_para_carreras(perfil, self._requisitos(perfil)),
            "cuota_usada": services.cuota_usada(perfil.usuario),
            "cuota_maxima": MAX_TOTAL_MB * 1024 * 1024,
            "archivo_maximo": MAX_ARCHIVO_MB * 1024 * 1024,
            "versiones_maximas": MAX_VERSIONES,
        }


class PerfilAspiranteEditarSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfilAspirante
        fields = ["centro_trabajo", "indice_declarado"]
        extra_kwargs = {"indice_declarado": {"coerce_to_string": False}}

    def validate_centro_trabajo(self, valor):
        return valor.strip()


class SubirDocumentoSerializer(serializers.Serializer):
    tipo = serializers.PrimaryKeyRelatedField(queryset=TipoDocumento.objects.filter(activo=True))
    archivo = serializers.FileField()

    def validate(self, attrs):
        try:
            attrs["formato"] = formato_documento(attrs["archivo"])
        except serializers.ValidationError as error:
            raise serializers.ValidationError({"archivo": error.detail})
        return attrs
