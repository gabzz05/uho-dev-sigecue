from rest_framework import serializers

from apps.core.ambito import es_de_su_entidad
from apps.core.serializers import ImagenOpcional

from .models import Area, Cargo, Carrera, CumFum, Departamento, Facultad, Municipio


class MunicipioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Municipio
        fields = ["id", "nombre", "provincia", "activo"]


class FacultadSerializer(serializers.ModelSerializer):
    municipio_nombre = serializers.CharField(source="municipio.nombre", read_only=True)
    imagen = ImagenOpcional()

    class Meta:
        model = Facultad
        fields = [
            "id", "nombre", "codigo", "descripcion", "decano", "telefono", "email",
            "municipio", "municipio_nombre", "imagen", "activo",
        ]


class CumFumSerializer(serializers.ModelSerializer):
    municipio_nombre = serializers.CharField(source="municipio.nombre", read_only=True)
    imagen = ImagenOpcional()

    class Meta:
        model = CumFum
        fields = [
            "id", "nombre", "codigo", "tipo", "director", "telefono", "email",
            "municipio", "municipio_nombre", "imagen", "activo",
        ]


class AreaSerializer(serializers.ModelSerializer):
    """Los roles locales solo crean y editan áreas de su propia entidad."""

    entidad_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Area
        fields = ["id", "nombre", "facultad", "cum_fum", "entidad_nombre", "activo"]
        # La regla "una sola entidad" se valida aquí con un mensaje claro.
        validators = []

    def get_entidad_nombre(self, area) -> str:
        return str(area.entidad)

    def validate(self, attrs):
        usuario = self.context["request"].user
        facultad = attrs.get("facultad", getattr(self.instance, "facultad", None))
        cum_fum = attrs.get("cum_fum", getattr(self.instance, "cum_fum", None))

        if facultad is None and cum_fum is None and not usuario.es_global:
            # Un rol local crea las áreas en su propia entidad sin tener que indicarla.
            facultad, cum_fum = usuario.facultad, usuario.cum_fum
            attrs["facultad"], attrs["cum_fum"] = facultad, cum_fum

        if (facultad is None) == (cum_fum is None):
            raise serializers.ValidationError({"facultad": "Indica una Facultad o un CUM/FUM (solo uno)."})
        if not es_de_su_entidad(usuario, facultad, cum_fum):
            raise serializers.ValidationError({"facultad": "Solo puedes gestionar áreas de tu propia entidad."})
        return attrs


class DepartamentoSerializer(serializers.ModelSerializer):
    area_nombre = serializers.CharField(source="area.nombre", read_only=True)

    class Meta:
        model = Departamento
        fields = ["id", "nombre", "area", "area_nombre", "activo"]

    def validate_area(self, area):
        usuario = self.context["request"].user
        if not es_de_su_entidad(usuario, area.facultad, area.cum_fum):
            raise serializers.ValidationError("Solo puedes gestionar departamentos de las áreas de tu entidad.")
        return area


class CargoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cargo
        fields = ["id", "nombre", "activo"]


class CarreraSerializer(serializers.ModelSerializer):
    imagen = ImagenOpcional()
    modalidad_nombre = serializers.CharField(source="get_modalidad_display", read_only=True)

    class Meta:
        model = Carrera
        fields = [
            "id", "nombre", "codigo", "modalidad", "modalidad_nombre", "duracion_anios", "descripcion",
            "objetivo", "perfil_egresado", "requisitos", "imagen", "activo",
        ]
