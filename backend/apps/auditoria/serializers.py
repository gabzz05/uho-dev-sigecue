from rest_framework import serializers

from .models import LogAuditoria


class LogAuditoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogAuditoria
        fields = [
            "id",
            "created_at",
            "usuario",
            "usuario_nombre",
            "accion",
            "modulo",
            "entidad_afectada",
            "entidad_id",
            "metodo",
            "ruta",
            "ip",
            "resultado",
            "codigo_http",
            "detalle",
        ]
        read_only_fields = fields
