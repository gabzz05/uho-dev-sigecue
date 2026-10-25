from rest_framework import serializers

from apps.core.serializers import ImagenOpcional

from . import plantillas
from .catalogo_plantillas import PLANTILLAS
from .models import ConfiguracionSistema, ConfiguracionSMTP, IdentidadVisual, PlantillaCorreo


class ParametrosSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionSistema
        fields = ["max_carreras_aspirante", "login_max_intentos", "login_bloqueo_minutos", "updated_at"]
        read_only_fields = ["updated_at"]


class SmtpSerializer(serializers.ModelSerializer):
    """La contraseña se puede escribir pero nunca se devuelve.
    Si no se envía (o llega vacía) se conserva la guardada."""

    password = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)
    password_configurada = serializers.SerializerMethodField()

    class Meta:
        model = ConfiguracionSMTP
        fields = [
            "activo", "host", "puerto", "usuario", "password", "password_configurada",
            "usar_tls", "usar_ssl", "remitente", "updated_at",
        ]
        read_only_fields = ["updated_at"]

    def get_password_configurada(self, smtp) -> bool:
        return bool(smtp.password)

    def validate(self, attrs):
        def valor(campo):
            return attrs.get(campo, getattr(self.instance, campo))

        if valor("usar_tls") and valor("usar_ssl"):
            raise serializers.ValidationError({"usar_ssl": "Elige STARTTLS o SSL/TLS, no ambos."})
        if valor("activo"):
            if not valor("host"):
                raise serializers.ValidationError({"host": "Indica el servidor SMTP."})
            if not valor("remitente"):
                raise serializers.ValidationError({"remitente": "Indica el remitente por defecto."})
        if not attrs.get("password"):
            attrs.pop("password", None)
        return attrs


class IdentidadSerializer(serializers.ModelSerializer):
    escudo = ImagenOpcional()

    class Meta:
        model = IdentidadVisual
        fields = ["nombre_institucion", "color_primario", "color_primario_claro", "color_acento", "escudo", "updated_at"]
        read_only_fields = ["updated_at"]


class PlantillaSerializer(serializers.ModelSerializer):
    nombre = serializers.SerializerMethodField()
    descripcion = serializers.SerializerMethodField()
    variables = serializers.SerializerMethodField()

    class Meta:
        model = PlantillaCorreo
        fields = ["codigo", "nombre", "descripcion", "variables", "asunto", "cuerpo", "updated_at"]
        read_only_fields = ["codigo", "updated_at"]

    def _catalogo(self, plantilla):
        return PLANTILLAS.get(plantilla.codigo, {})

    def get_nombre(self, plantilla) -> str:
        return self._catalogo(plantilla).get("nombre", plantilla.codigo)

    def get_descripcion(self, plantilla) -> str:
        return self._catalogo(plantilla).get("descripcion", "")

    def get_variables(self, plantilla) -> dict[str, str]:
        """Variables disponibles: nombre → descripción."""
        return self._catalogo(plantilla).get("variables", {})

    def validate(self, attrs):
        permitidas = self._catalogo(self.instance).get("variables", {})
        for campo in ("asunto", "cuerpo"):
            if campo in attrs and (desconocidas := plantillas.variables_desconocidas(attrs[campo], permitidas)):
                raise serializers.ValidationError(
                    {campo: f"Variables no disponibles en esta plantilla: {', '.join(desconocidas)}."}
                )
        return attrs


class VistaPreviaSerializer(serializers.Serializer):
    asunto = serializers.CharField(allow_blank=True)
    cuerpo = serializers.CharField(allow_blank=True)


class PruebaSmtpSerializer(serializers.Serializer):
    destinatario = serializers.EmailField()
