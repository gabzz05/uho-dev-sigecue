from rest_framework import serializers

from .validators import validar_imagen


class ImagenOpcional(serializers.ImageField):
    """Imagen validada (tipo y tamaño). Enviar el campo vacío la elimina."""

    def __init__(self, **kwargs):
        super().__init__(required=False, allow_null=True, validators=[validar_imagen], **kwargs)

    def to_internal_value(self, data):
        if data in ("", None):
            return None
        return super().to_internal_value(data)
