from rest_framework import serializers

from apps.nomencladores.models import CumFum, Facultad

from . import services
from .models import ConvocatoriaSolicitud


class ConvocatoriaSolicitudSerializer(serializers.ModelSerializer):
    estado_nombre = serializers.CharField(source="get_estado_display", read_only=True)
    facultades = serializers.PrimaryKeyRelatedField(many=True, queryset=Facultad.objects.filter(activo=True), required=False)
    cum_fums = serializers.PrimaryKeyRelatedField(many=True, queryset=CumFum.objects.filter(activo=True), required=False)
    entidades = serializers.SerializerMethodField()
    total_ofertas = serializers.SerializerMethodField()

    class Meta:
        model = ConvocatoriaSolicitud
        fields = [
            "id", "anio_academico", "numero", "fecha_inicio", "fecha_cierre", "mensaje_publico", "estado", "estado_nombre",
            "facultades", "cum_fums", "entidades", "total_ofertas", "interesados_notificados", "created_at",
        ]
        read_only_fields = ["numero", "estado", "interesados_notificados", "created_at"]
        validators = []  # Fechas y unicidad se validan con mensajes claros.

    def get_entidades(self, convocatoria) -> list[str]:
        """Nombres de las entidades seleccionadas; vacío = todas las que tienen plazas."""
        return [f.nombre for f in convocatoria.facultades.all()] + [c.nombre for c in convocatoria.cum_fums.all()]

    def get_total_ofertas(self, convocatoria) -> int:
        return services.ofertas_de(convocatoria).count()

    def validate(self, attrs):
        inicio = attrs.get("fecha_inicio", getattr(self.instance, "fecha_inicio", None))
        cierre = attrs.get("fecha_cierre", getattr(self.instance, "fecha_cierre", None))
        if inicio and cierre and cierre < inicio:
            raise serializers.ValidationError({"fecha_cierre": "La fecha de cierre no puede ser anterior a la de inicio."})
        if self.instance and "anio_academico" in attrs and attrs["anio_academico"] != self.instance.anio_academico:
            raise serializers.ValidationError({"anio_academico": "El año académico de una convocatoria no se cambia."})
        return attrs


class ConvocatoriaSolicitudPublicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConvocatoriaSolicitud
        fields = ["anio_academico", "numero", "fecha_inicio", "fecha_cierre", "mensaje_publico"]
