from rest_framework import serializers

from .models import Permiso, Rol


class RolSerializer(serializers.ModelSerializer):
    """Los permisos se leen y escriben como códigos `modulo.accion`."""

    permisos = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)

    class Meta:
        model = Rol
        fields = ["id", "codigo", "nombre", "descripcion", "ambito", "requiere_area", "es_sistema", "activo", "permisos"]
        read_only_fields = ["es_sistema"]

    def to_representation(self, rol):
        datos = super().to_representation(rol)
        datos["permisos"] = sorted(p.codigo for p in rol.permisos.all())
        return datos

    def validate_permisos(self, codigos):
        por_codigo = {p.codigo: p for p in Permiso.objects.all()}
        invalidos = sorted(set(codigos) - por_codigo.keys())
        if invalidos:
            raise serializers.ValidationError(f"Permisos inexistentes: {', '.join(invalidos)}.")
        return [por_codigo[c] for c in set(codigos)]

    def validate(self, attrs):
        rol = self.instance
        if rol is not None and rol.es_sistema:
            for campo in ("codigo", "ambito"):
                if campo in attrs and attrs[campo] != getattr(rol, campo):
                    raise serializers.ValidationError(
                        {campo: "No se puede cambiar en un rol del sistema."}
                    )
        return attrs

    def create(self, validated_data):
        permisos = validated_data.pop("permisos", [])
        rol = super().create(validated_data)
        rol.permisos.set(permisos)
        return rol

    def update(self, rol, validated_data):
        permisos = validated_data.pop("permisos", None)
        rol = super().update(rol, validated_data)
        if permisos is not None:
            rol.permisos.set(permisos)
        return rol
