from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.validators import formato_documento
from apps.otorgamiento.models import Otorgamiento

from . import services
from .models import MAX_TOTAL_MB, ArchivoPrematricula, CampoPrematricula, ElementoPrematricula, PeriodoPrematricula, Prematricula


class CampoPrematriculaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampoPrematricula
        fields = ["id", "nombre", "tipo", "requerido", "orden", "activo"]


class PeriodoSerializer(serializers.ModelSerializer):
    convocatoria = serializers.SerializerMethodField()
    abierto = serializers.BooleanField(read_only=True)
    cerrado = serializers.BooleanField(read_only=True)

    class Meta:
        model = PeriodoPrematricula
        fields = ["id", "otorgamiento", "convocatoria", "fecha_inicio", "fecha_cierre", "abierto", "cerrado"]

    def get_convocatoria(self, periodo) -> str:
        c = periodo.otorgamiento.convocatoria
        return f"{c.numero}.ª convocatoria {c.anio_academico}"


class ConfigurarPeriodoSerializer(serializers.Serializer):
    otorgamiento = serializers.PrimaryKeyRelatedField(queryset=Otorgamiento.objects.all())
    fecha_inicio = serializers.DateField()
    fecha_cierre = serializers.DateField()


class ArchivoSerializer(serializers.ModelSerializer):
    archivo = serializers.SerializerMethodField(help_text="Ruta de la API para descargarlo (requiere el token).")

    class Meta:
        model = ArchivoPrematricula
        fields = ["id", "version", "nombre_original", "formato", "tamano", "subido_at", "archivo"]

    def get_archivo(self, a) -> str:
        return f"/prematricula/archivos/{a.pk}/"


class ElementoSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(read_only=True)
    tipo = serializers.SerializerMethodField(help_text="documento_perfil, texto, archivo o imagen")
    requerido = serializers.SerializerMethodField()
    entregado = serializers.SerializerMethodField()
    revision_nombre = serializers.CharField(source="get_revision_display", read_only=True)
    archivo = serializers.SerializerMethodField(help_text="Archivo vigente (campos) o documento vigente del perfil.")
    editable = serializers.SerializerMethodField()

    class Meta:
        model = ElementoPrematricula
        fields = [
            "id", "nombre", "tipo", "requerido", "campo", "tipo_documento", "valor_texto", "entregado",
            "revision", "revision_nombre", "observacion", "revisado_at", "archivo", "editable",
        ]

    def get_tipo(self, e) -> str:
        return "documento_perfil" if e.tipo_documento_id else e.campo.tipo

    def get_requerido(self, e) -> bool:
        return services.requerido(e)

    def get_entregado(self, e) -> bool:
        return services.tiene_valor(e)

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_archivo(self, e):
        if e.tipo_documento_id:
            documento = services.documento_vigente(e.prematricula, e.tipo_documento_id)
            if documento is None:
                return None
            return {
                "id": documento.pk, "version": documento.version, "nombre_original": documento.nombre_original,
                "formato": documento.formato, "tamano": documento.tamano, "subido_at": documento.subido_at,
                "archivo": f"/documentos/{documento.pk}/archivo/",
            }
        vigente = e.archivos.filter(vigente=True).first()
        return ArchivoSerializer(vigente).data if vigente else None

    def get_editable(self, e) -> bool:
        return services.puede_editar_elemento(e.prematricula, e)


class PrematriculaSerializer(serializers.ModelSerializer):
    estado_nombre = serializers.CharField(source="get_estado_display", read_only=True)
    periodo = PeriodoSerializer(read_only=True)
    aspirante_nombre = serializers.CharField(source="resultado.aspirante_nombre", read_only=True)
    carrera = serializers.CharField(source="resultado.carrera", read_only=True)
    entidad = serializers.CharField(source="resultado.entidad", read_only=True)
    faltantes = serializers.SerializerMethodField()
    aprobado_por = serializers.SerializerMethodField()

    class Meta:
        model = Prematricula
        fields = [
            "id", "estado", "estado_nombre", "periodo", "aspirante", "aspirante_nombre", "carrera", "entidad",
            "faltantes", "enviada_at", "fecha_aprobacion", "aprobado_por", "updated_at",
        ]

    def get_faltantes(self, p) -> list[str]:
        return [e.nombre for e in services.faltantes(p)]

    def get_aprobado_por(self, p) -> str | None:
        return p.aprobado_por.nombre_completo if p.aprobado_por else None


class PrematriculaDetalleSerializer(PrematriculaSerializer):
    elementos = serializers.SerializerMethodField()
    limites = serializers.SerializerMethodField()
    permisos = serializers.SerializerMethodField()

    class Meta(PrematriculaSerializer.Meta):
        fields = PrematriculaSerializer.Meta.fields + ["elementos", "limites", "permisos"]

    @extend_schema_field(ElementoSerializer(many=True))
    def get_elementos(self, p):
        services.sincronizar_elementos(p)
        elementos = p.elementos.select_related("campo", "tipo_documento", "prematricula__periodo").prefetch_related("archivos")
        ordenados = sorted(elementos, key=lambda e: (0, e.tipo_documento.orden) if e.tipo_documento_id else (1, e.campo.orden))
        return ElementoSerializer(ordenados, many=True).data

    @extend_schema_field(serializers.DictField())
    def get_limites(self, p):
        return {"cuota_usada": services.cuota_usada(p.aspirante), "cuota_maxima": MAX_TOTAL_MB * 1024 * 1024}

    @extend_schema_field(serializers.DictField())
    def get_permisos(self, p):
        usuario = self.context["request"].user
        revisa = services.puede_revisar(usuario, p) and p.estado == Prematricula.Estado.COMPLETADA
        return {"revisar": revisa, "descargar": services.puede_descargar(usuario, p), "enviar": usuario.pk == p.aspirante_id}


class TextoPrematriculaSerializer(serializers.Serializer):
    elemento = serializers.PrimaryKeyRelatedField(queryset=ElementoPrematricula.objects.select_related("campo"))
    valor = serializers.CharField(allow_blank=True, max_length=2000)


class SubirArchivoSerializer(serializers.Serializer):
    elemento = serializers.PrimaryKeyRelatedField(queryset=ElementoPrematricula.objects.select_related("campo"))
    archivo = serializers.FileField()

    def validate(self, attrs):
        try:
            attrs["formato"] = formato_documento(attrs["archivo"])
        except serializers.ValidationError as error:
            raise serializers.ValidationError({"archivo": error.detail})
        return attrs


class RevisarSerializer(serializers.Serializer):
    elemento = serializers.PrimaryKeyRelatedField(queryset=ElementoPrematricula.objects.select_related("campo", "tipo_documento"))
    revision = serializers.ChoiceField([ElementoPrematricula.Revision.APROBADO, ElementoPrematricula.Revision.RECHAZADO])
    observacion = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")
