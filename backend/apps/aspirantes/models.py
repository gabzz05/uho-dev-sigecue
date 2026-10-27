import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

# RNF-005: 5 MB por archivo y 20 MB por aspirante. Cuentan los archivos
# vigentes (documentos y foto); el historial queda fuera de la cuota pero
# limitado a MAX_VERSIONES por documento.
MAX_TOTAL_MB = 20
MAX_VERSIONES = 10


class PerfilAspirante(models.Model):
    """Datos del aspirante que no están en su cuenta (RF-046).

    Nombre, apellidos, CI, email, celular y foto viven en `Usuario`.
    `perfil_completo` es una caché: la fuente de verdad es
    `services.requisitos_perfil`, que se recalcula con cada cambio.
    """

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name="usuario", on_delete=models.CASCADE, related_name="perfil_aspirante")
    centro_trabajo = models.CharField("centro de trabajo actual", max_length=200, blank=True)
    indice_declarado = models.DecimalField(
        "índice académico declarado", max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    # Lo fija una sola entidad al validar la certificación; después solo un rol
    # global lo cambia. Es obligatorio para entrar al ranking del otorgamiento.
    indice_validado = models.DecimalField(
        "índice académico validado", max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    indice_validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="índice validado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    indice_validado_at = models.DateTimeField("índice validado el", null=True, blank=True)
    perfil_completo = models.BooleanField("perfil completo", default=False, editable=False)
    created_at = models.DateTimeField("creado", auto_now_add=True)
    updated_at = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "perfil de aspirante"
        verbose_name_plural = "perfiles de aspirante"

    def __str__(self):
        return f"Perfil de {self.usuario.nombre_completo}"


class TipoDocumento(models.Model):
    """Documento que sube el aspirante con su perfil (CI anverso, CI reverso, certificación...).

    Catálogo dinámico que gestiona el Superadmin. Formatos (PDF, JPG, PNG) y
    tamaño máximo son comunes a todos los tipos.
    """

    nombre = models.CharField("nombre", max_length=100, unique=True)
    obligatorio = models.BooleanField("obligatorio", default=True)
    # Valor por defecto de `afecta_elegibilidad` en las observaciones sobre este documento.
    afecta_elegibilidad = models.BooleanField(
        "una observación afecta la elegibilidad", default=False,
        help_text="Si se observa, se anula el índice validado y hay que volver a validarlo.",
    )
    activo = models.BooleanField("activo", default=True)
    orden = models.PositiveSmallIntegerField("orden", default=0)

    class Meta:
        verbose_name = "tipo de documento"
        verbose_name_plural = "tipos de documento"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


def ruta_documento(documento, nombre):
    extension = nombre.rsplit(".", 1)[-1].lower()
    return f"aspirantes/{documento.perfil.usuario_id}/documentos/{uuid.uuid4().hex}.{extension}"


class DocumentoAspirante(models.Model):
    """Una versión de un documento del aspirante.

    Cada sustitución crea una versión nueva; la vigente es la única con
    `vigente=True`. Las anteriores se conservan como evidencia de lo revisado
    hasta que la política de retención las purgue (como máximo MAX_VERSIONES
    por documento: al superarlo se borra la más antigua).
    """

    perfil = models.ForeignKey(PerfilAspirante, verbose_name="perfil", on_delete=models.CASCADE, related_name="documentos")
    tipo = models.ForeignKey(TipoDocumento, verbose_name="tipo", on_delete=models.PROTECT, related_name="documentos")
    version = models.PositiveSmallIntegerField("versión")
    vigente = models.BooleanField("vigente", default=True)
    archivo = models.FileField("archivo", upload_to=ruta_documento)
    nombre_original = models.CharField("nombre original", max_length=255)
    formato = models.CharField("formato", max_length=4)
    tamano = models.PositiveIntegerField("tamaño (bytes)")
    subido_at = models.DateTimeField("subido", auto_now_add=True)

    class Meta:
        verbose_name = "documento de aspirante"
        verbose_name_plural = "documentos de aspirante"
        ordering = ["tipo__orden", "tipo__nombre", "-version"]
        constraints = [
            models.UniqueConstraint(fields=["perfil", "tipo", "version"], name="documento_version_unica"),
            models.UniqueConstraint(fields=["perfil", "tipo"], condition=Q(vigente=True), name="documento_un_vigente"),
        ]

    def __str__(self):
        return f"{self.tipo} v{self.version} de {self.perfil.usuario.nombre_completo}"
