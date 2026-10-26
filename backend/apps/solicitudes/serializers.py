from rest_framework import serializers

from apps.configuracion.services import parametros
from apps.oferta.models import OfertaCarrera

from .models import Solicitud, SolicitudCarrera


class OfertaElegibleSerializer(serializers.ModelSerializer):
    """Carrera + entidad que el aspirante puede elegir en la convocatoria."""

    carrera_nombre = serializers.CharField(source="carrera.nombre")
    duracion_anios = serializers.IntegerField(source="carrera.duracion_anios")
    tipo_entidad = serializers.SerializerMethodField()
    entidad_nombre = serializers.CharField(source="entidad.nombre")
    municipio = serializers.CharField(source="entidad.municipio.nombre")
    plazas = serializers.IntegerField(source="plazas_plan")

    class Meta:
        model = OfertaCarrera
        fields = ["id", "carrera", "carrera_nombre", "duracion_anios", "tipo_entidad", "entidad_nombre", "municipio", "plazas"]

    def get_tipo_entidad(self, oferta) -> str:
        return "facultad" if oferta.facultad_id else "cum_fum"


class SolicitudCarreraSerializer(serializers.ModelSerializer):
    oferta = OfertaElegibleSerializer()
    estado_nombre = serializers.CharField(source="get_estado_display")

    class Meta:
        model = SolicitudCarrera
        fields = ["prioridad", "estado", "estado_nombre", "oferta"]


class SolicitudSerializer(serializers.ModelSerializer):
    convocatoria = serializers.SerializerMethodField()
    estado_nombre = serializers.CharField(source="get_estado_display", read_only=True)
    editable = serializers.BooleanField(read_only=True)
    carreras = SolicitudCarreraSerializer(many=True, read_only=True)
    max_carreras = serializers.SerializerMethodField()

    class Meta:
        model = Solicitud
        fields = [
            "id", "convocatoria", "estado", "estado_nombre", "editable", "created_at", "confirmada_at", "modificada_at",
            "carreras", "max_carreras",
        ]

    def get_convocatoria(self, solicitud) -> dict:
        c = solicitud.convocatoria
        return {
            "id": c.pk, "anio_academico": c.anio_academico, "numero": c.numero,
            "fecha_inicio": c.fecha_inicio, "fecha_cierre": c.fecha_cierre, "acepta_solicitudes": c.acepta_solicitudes,
        }

    def get_max_carreras(self, solicitud) -> int:
        return parametros().max_carreras_aspirante


class GuardarCarrerasSerializer(serializers.Serializer):
    ofertas = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=True, help_text="Ids de OfertaCarrera en orden de prioridad (la primera es la 1)."
    )

    def validate_ofertas(self, ids):
        encontradas = OfertaCarrera.objects.select_related("carrera", "facultad", "cum_fum").in_bulk(ids)
        if faltan := [i for i in ids if i not in encontradas]:
            raise serializers.ValidationError(f"No existe la oferta {faltan[0]}.")
        return [encontradas[i] for i in ids]
