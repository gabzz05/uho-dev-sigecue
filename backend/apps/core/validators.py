from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

MAX_IMAGEN_MB = 5  # RNF-005
MAX_ARCHIVO_MB = 5  # RNF-005
FORMATOS_IMAGEN = {"JPEG", "PNG", "WEBP"}
FORMATOS_FOTO_ASPIRANTE = {"JPEG", "PNG"}
FORMATOS_DOCUMENTO = {"PDF", "JPEG", "PNG"}
EXTENSION = {"PDF": "pdf", "JPEG": "jpg", "PNG": "png"}
TIPO_MIME = {"PDF": "application/pdf", "JPEG": "image/jpeg", "PNG": "image/png"}


def validar_imagen(archivo, formatos=FORMATOS_IMAGEN):
    """Tamaño y formato real de la imagen (Pillow ya verificó que es una imagen válida)."""
    if archivo.size > MAX_IMAGEN_MB * 1024 * 1024:
        raise serializers.ValidationError(f"La imagen no puede superar {MAX_IMAGEN_MB} MB.")
    formato = getattr(getattr(archivo, "image", None), "format", None)
    if formato not in formatos:
        nombres = ", ".join("JPG" if f == "JPEG" else f for f in sorted(formatos))
        raise serializers.ValidationError(f"La imagen debe ser {nombres}.")
    return archivo


def formato_documento(archivo):
    """Formato real (por contenido, no por extensión) de un documento del aspirante: PDF, JPEG o PNG.

    Valida también el tamaño máximo por archivo (RNF-005).
    """
    if archivo.size > MAX_ARCHIVO_MB * 1024 * 1024:
        raise serializers.ValidationError(f"El archivo no puede superar {MAX_ARCHIVO_MB} MB.")
    archivo.seek(0)
    cabecera = archivo.read(5)
    archivo.seek(0)
    if cabecera == b"%PDF-":
        return "PDF"
    try:
        with Image.open(archivo) as imagen:
            formato = imagen.format
            imagen.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        formato = None
    finally:
        archivo.seek(0)
    if formato not in FORMATOS_DOCUMENTO:
        raise serializers.ValidationError("El archivo debe ser PDF, JPG o PNG.")
    return formato
