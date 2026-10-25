from django.core.validators import RegexValidator
from rest_framework import serializers

from apps.core import crypto
from apps.users.models import Usuario

validar_ci = RegexValidator(r"^\d{11}$", "El carnet de identidad debe tener 11 dígitos, sin espacios ni guiones.")
validar_celular = RegexValidator(r"^5\d{7}$", "El celular debe tener 8 dígitos y empezar por 5.")

MAX_IMAGEN_MB = 5  # RNF-005
FORMATOS_IMAGEN = {"JPEG", "PNG", "WEBP"}


def validar_imagen(archivo):
    """Tamaño y formato real de la imagen (Pillow ya verificó que es una imagen válida)."""
    if archivo.size > MAX_IMAGEN_MB * 1024 * 1024:
        raise serializers.ValidationError(f"La imagen no puede superar {MAX_IMAGEN_MB} MB.")
    formato = getattr(getattr(archivo, "image", None), "format", None)
    if formato not in FORMATOS_IMAGEN:
        raise serializers.ValidationError("La imagen debe ser JPG, PNG o WEBP.")
    return archivo


def validar_unico(campo_hash, valor, mensaje, excluir=None):
    qs = Usuario.objects.filter(**{campo_hash: crypto.hash_busqueda(valor)})
    if excluir is not None:
        qs = qs.exclude(pk=excluir.pk)
    if qs.exists():
        raise serializers.ValidationError(mensaje)
    return valor
