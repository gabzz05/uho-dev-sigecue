from rest_framework import serializers

from .models import EnvioMasivo, Notificacion
from .services import TIPOS_GRUPO


class NotificacionSerializer(serializers.ModelSerializer):
    resumen = serializers.SerializerMethodField()

    class Meta:
        model = Notificacion
        fields = ["id", "tipo", "asunto", "resumen", "cuerpo", "leida", "leida_at", "created_at"]
        read_only_fields = fields

    def get_resumen(self, notificacion) -> str:
        """Primeras líneas del cuerpo, para la lista (RF-074)."""
        texto = " ".join(notificacion.cuerpo.split())
        return texto if len(texto) <= 140 else f"{texto[:137].rstrip()}…"


class GrupoSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=TIPOS_GRUPO)
    rol = serializers.CharField(required=False)
    facultad = serializers.IntegerField(required=False)
    cum_fum = serializers.IntegerField(required=False)


class EnvioMasivoSerializer(serializers.ModelSerializer):
    grupo = GrupoSerializer()
    enviado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = EnvioMasivo
        fields = [
            "id", "grupo", "grupo_descripcion", "asunto", "cuerpo", "por_correo",
            "destinatarios", "enviado_por_nombre", "created_at",
        ]
        read_only_fields = ["grupo_descripcion", "destinatarios", "enviado_por_nombre", "created_at"]

    def get_enviado_por_nombre(self, envio) -> str:
        usuario = envio.enviado_por
        return (usuario.nombre_completo or usuario.username) if usuario else ""
