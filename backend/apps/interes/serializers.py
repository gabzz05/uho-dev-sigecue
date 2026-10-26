from rest_framework import serializers

from apps.nomencladores.models import Carrera
from apps.oferta.models import OfertaCarrera
from apps.users.validators import validar_celular, validar_ci

from .models import ConvocatoriaInteres, ExpresionInteres

# --- Panel ---------------------------------------------------------------------


class ConvocatoriaInteresSerializer(serializers.ModelSerializer):
    estado_nombre = serializers.CharField(source="get_estado_display", read_only=True)
    total_ofertas = serializers.SerializerMethodField()
    total_interesados = serializers.SerializerMethodField()

    class Meta:
        model = ConvocatoriaInteres
        fields = [
            "id", "anio_academico", "fecha_inicio", "fecha_cierre", "mensaje_publico",
            "estado", "estado_nombre", "total_ofertas", "total_interesados", "created_at",
        ]
        read_only_fields = ["estado", "created_at"]
        validators = []  # Las fechas se validan abajo con un mensaje claro.

    def get_total_ofertas(self, convocatoria) -> int:
        return OfertaCarrera.objects.filter(anio_academico=convocatoria.anio_academico).count()

    def get_total_interesados(self, convocatoria) -> int:
        return convocatoria.expresiones.count()

    def validate(self, attrs):
        inicio = attrs.get("fecha_inicio", getattr(self.instance, "fecha_inicio", None))
        cierre = attrs.get("fecha_cierre", getattr(self.instance, "fecha_cierre", None))
        if inicio and cierre and cierre < inicio:
            raise serializers.ValidationError({"fecha_cierre": "La fecha de cierre no puede ser anterior a la de inicio."})
        if self.instance and "anio_academico" in attrs and attrs["anio_academico"] != self.instance.anio_academico:
            if self.instance.estado != ConvocatoriaInteres.Estado.BORRADOR:
                raise serializers.ValidationError({"anio_academico": "Solo se cambia el año en una convocatoria en borrador."})
            if OfertaCarrera.objects.filter(anio_academico=self.instance.anio_academico).exists():
                raise serializers.ValidationError({"anio_academico": "Quita la oferta antes de cambiar el año."})
        return attrs


def _entidad(oferta):
    entidad = oferta.entidad
    return {
        "tipo": "facultad" if oferta.facultad_id else "cum_fum",
        "id": entidad.pk,
        "nombre": entidad.nombre,
        "municipio": entidad.municipio.nombre,
    }


class OfertaSerializer(serializers.ModelSerializer):
    convocatoria = serializers.PrimaryKeyRelatedField(queryset=ConvocatoriaInteres.objects.all(), write_only=True)
    carrera_nombre = serializers.CharField(source="carrera.nombre", read_only=True)
    entidad = serializers.SerializerMethodField()
    total_interesados = serializers.IntegerField(read_only=True)

    class Meta:
        model = OfertaCarrera
        fields = [
            "id", "convocatoria", "carrera", "carrera_nombre", "facultad", "cum_fum", "entidad",
            "anio_academico", "asignada_por_ci", "total_interesados", "created_at",
        ]
        read_only_fields = ["anio_academico", "asignada_por_ci", "created_at"]
        validators = []  # Unicidad y entidad las valida el service con mensajes claros.

    def get_entidad(self, oferta) -> dict:
        return _entidad(oferta)


class ExpresionInteresSerializer(serializers.ModelSerializer):
    """Datos personales completos: solo para roles internos dentro de su ámbito."""

    carrera = serializers.CharField(source="oferta.carrera.nombre", read_only=True)
    entidad = serializers.SerializerMethodField()
    anio_academico = serializers.CharField(source="oferta.anio_academico", read_only=True)

    class Meta:
        model = ExpresionInteres
        fields = ["id", "nombre", "ci", "celular", "email", "carrera", "entidad", "anio_academico", "created_at"]
        read_only_fields = fields

    def get_entidad(self, expresion) -> str:
        return str(expresion.oferta.entidad)


# --- Público -------------------------------------------------------------------


class CarreraPublicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrera
        fields = ["id", "nombre", "duracion_anios", "descripcion", "objetivo", "perfil_egresado", "requisitos", "imagen"]


class OfertaPublicaSerializer(serializers.ModelSerializer):
    """Una tarjeta de la landing: carrera + entidad + municipio (RF-020). Sin datos personales."""

    carrera = CarreraPublicaSerializer(read_only=True)
    entidad = serializers.SerializerMethodField()

    class Meta:
        model = OfertaCarrera
        fields = ["id", "carrera", "entidad", "anio_academico"]

    def get_entidad(self, oferta) -> dict:
        return _entidad(oferta)


class ConvocatoriaPublicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConvocatoriaInteres
        fields = ["anio_academico", "fecha_inicio", "fecha_cierre", "mensaje_publico"]


class RegistroInteresSerializer(serializers.Serializer):
    oferta = serializers.PrimaryKeyRelatedField(queryset=OfertaCarrera.objects.select_related("carrera"))
    nombre = serializers.CharField(max_length=200)
    ci = serializers.CharField(validators=[validar_ci])
    celular = serializers.CharField(validators=[validar_celular])
    email = serializers.EmailField()
    acepta_privacidad = serializers.BooleanField()

    def validate_nombre(self, nombre):
        nombre = " ".join(nombre.split())
        if len(nombre) < 3:
            raise serializers.ValidationError("Escribe tu nombre completo.")
        return nombre

    def validate_acepta_privacidad(self, acepta):
        if not acepta:
            raise serializers.ValidationError("Debes aceptar la política de privacidad.")
        return acepta
