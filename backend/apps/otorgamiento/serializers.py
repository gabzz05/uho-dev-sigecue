from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.convocatorias.models import ConvocatoriaSolicitud
from apps.roles.catalogo import APROBAR, EXPORTAR, PUBLICAR
from apps.solicitudes.models import SolicitudCarrera

from . import services
from .models import AjusteOtorgamiento, Otorgamiento, ResultadoOtorgamiento


def _nombre(usuario):
    return usuario.nombre_completo if usuario else None


class OtorgamientoSerializer(serializers.ModelSerializer):
    convocatoria = serializers.SerializerMethodField()
    estado_nombre = serializers.CharField(source="get_estado_display")
    generado_por = serializers.SerializerMethodField()
    aprobado_por = serializers.SerializerMethodField()
    publicado_por = serializers.SerializerMethodField()
    totales = serializers.SerializerMethodField()
    plazas = serializers.SerializerMethodField()
    permisos = serializers.SerializerMethodField()

    class Meta:
        model = Otorgamiento
        fields = [
            "id", "convocatoria", "estado", "estado_nombre", "resumen", "segunda_convocatoria",
            "generado_por", "generado_at", "aprobado_por", "aprobado_at", "publicado_por", "publicado_at",
            "totales", "plazas", "permisos",
        ]

    def _usuario(self):
        return self.context["request"].user

    def get_convocatoria(self, o) -> dict:
        c = o.convocatoria
        return {"id": c.pk, "anio_academico": c.anio_academico, "numero": c.numero}

    def get_generado_por(self, o) -> str | None:
        return _nombre(o.generado_por)

    def get_aprobado_por(self, o) -> str | None:
        return _nombre(o.aprobado_por)

    def get_publicado_por(self, o) -> str | None:
        return _nombre(o.publicado_por)

    @extend_schema_field(serializers.DictField())
    def get_totales(self, o):
        resultados = services.resultados_visibles(self._usuario(), o)
        return {
            "resultados": resultados.count(),
            "elegibles": resultados.filter(posicion_ranking__isnull=False).count(),
            "otorgadas": resultados.filter(otorgada__isnull=False).count(),
            "plazas": sum(f["plazas"] for f in services.plazas_por_oferta(o, self._usuario())),
        }

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_plazas(self, o):
        return services.plazas_por_oferta(o, self._usuario())

    @extend_schema_field(serializers.DictField())
    def get_permisos(self, o):
        usuario = self._usuario()
        etapa = services.permiso_de_etapa(o)
        return {
            "editar": services.puede_editar(usuario, o),
            "aprobar": etapa == APROBAR and usuario.tiene_permiso(services.MODULO, APROBAR),
            "publicar": etapa == PUBLICAR and usuario.tiene_permiso(services.MODULO, PUBLICAR),
            "exportar": usuario.tiene_permiso(services.MODULO, EXPORTAR),
        }


class ResultadoSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source="get_tipo_display")
    opciones_quitadas = serializers.SerializerMethodField(help_text="Opciones que un ajuste vigente le quitó.")

    class Meta:
        model = ResultadoOtorgamiento
        fields = [
            "id", "solicitud", "aspirante", "aspirante_nombre", "indice_utilizado", "confirmada_at", "posicion_ranking",
            "motivo_exclusion", "opciones", "otorgada", "carrera", "entidad", "prioridad", "tipo", "tipo_nombre", "opciones_quitadas",
        ]
        extra_kwargs = {"indice_utilizado": {"coerce_to_string": False}}

    def get_opciones_quitadas(self, r) -> list[int]:
        return [a.opcion_id for a in r.ajustes.all() if a.activo and a.tipo == AjusteOtorgamiento.Tipo.QUITAR]


class AjusteSerializer(serializers.ModelSerializer):
    aspirante = serializers.CharField(source="resultado.aspirante_nombre", read_only=True)
    tipo_nombre = serializers.CharField(source="get_tipo_display", read_only=True)
    opcion_texto = serializers.SerializerMethodField()
    usuario = serializers.SerializerMethodField()
    anulado_por = serializers.SerializerMethodField()

    class Meta:
        model = AjusteOtorgamiento
        fields = [
            "id", "resultado", "aspirante", "tipo", "tipo_nombre", "opcion", "opcion_texto", "justificacion", "usuario", "created_at",
            "cambios", "activo", "anulado_por", "anulado_at", "justificacion_anulacion",
        ]

    def get_opcion_texto(self, a) -> str:
        return f"{a.opcion.oferta.carrera.nombre} — {a.opcion.oferta.entidad}"

    def get_usuario(self, a) -> str | None:
        return _nombre(a.usuario)

    def get_anulado_por(self, a) -> str | None:
        return _nombre(a.anulado_por)


class GenerarSerializer(serializers.Serializer):
    convocatoria = serializers.PrimaryKeyRelatedField(queryset=ConvocatoriaSolicitud.objects.all())
    confirmar = serializers.BooleanField(help_text="Debe ser true: la Secretaria General confirma tras ver el resumen.")

    def validate_confirmar(self, valor):
        if not valor:
            raise serializers.ValidationError("Revisa el resumen de elegibilidad y confirma la generación.")
        return valor


class AjustarSerializer(serializers.Serializer):
    resultado = serializers.PrimaryKeyRelatedField(queryset=ResultadoOtorgamiento.objects.all())
    tipo = serializers.ChoiceField(AjusteOtorgamiento.Tipo.choices)
    opcion = serializers.PrimaryKeyRelatedField(queryset=SolicitudCarrera.objects.select_related("oferta"))
    justificacion = serializers.CharField(max_length=2000)


class AnularAjusteSerializer(serializers.Serializer):
    justificacion = serializers.CharField(max_length=2000)


class PublicarSerializer(serializers.Serializer):
    segunda_convocatoria = serializers.BooleanField(help_text="Cambia el aviso a los no seleccionados (RF-061).")

