from rest_framework import serializers

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
