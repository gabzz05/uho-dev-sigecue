import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

# Cuota propia de la prematrícula, separada de la del perfil (decisión del cliente).
MAX_TOTAL_MB = 20
MAX_VERSIONES = 10


class PeriodoPrematricula(models.Model):
    """Período de prematrícula de un otorgamiento publicado (RF-067, RF-070). Lo fija la Secretaría General.

    Su cierre es también el último día del listado público de resultados.
    """

    otorgamiento = models.OneToOneField(
        "otorgamiento.Otorgamiento", verbose_name="otorgamiento", on_delete=models.PROTECT, related_name="periodo_prematricula"
    )
    fecha_inicio = models.DateField("fecha de inicio")
    fecha_cierre = models.DateField("fecha de cierre")
    configurado_por = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="configurado por", null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField("configurado", auto_now_add=True)
    # Avisos ya enviados, para que la tarea diaria no los repita.
    aviso_apertura_enviado = models.BooleanField(default=False)
    recordatorio_5_enviado = models.BooleanField(default=False)
    recordatorio_1_enviado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "período de prematrícula"
        verbose_name_plural = "períodos de prematrícula"
        constraints = [
            models.CheckConstraint(
                condition=Q(fecha_cierre__gte=F("fecha_inicio")),
                name="periodo_prematricula_fechas",
                violation_error_message="La fecha de cierre no puede ser anterior a la de inicio.",
            ),
        ]

    def __str__(self):
        return f"Prematrícula de {self.otorgamiento.convocatoria}"

    @property
    def abierto(self) -> bool:
        return self.fecha_inicio <= timezone.localdate() <= self.fecha_cierre

    @property
    def cerrado(self) -> bool:
        return timezone.localdate() > self.fecha_cierre


class CampoPrematricula(models.Model):
    """Campo o documento que pide el formulario de prematrícula (RF-010, RF-066). Lo gestiona el Superadmin.

    CI y certificación no están aquí: se reutilizan del perfil del aspirante.
    """

    class Tipo(models.TextChoices):
        TEXTO = "texto", "Texto"
        ARCHIVO = "archivo", "Archivo (PDF, JPG o PNG)"
        IMAGEN = "imagen", "Imagen (JPG o PNG)"

    nombre = models.CharField("nombre", max_length=100, unique=True)
    tipo = models.CharField("tipo", max_length=8, choices=Tipo.choices)
    requerido = models.BooleanField("requerido", default=True)
    orden = models.PositiveSmallIntegerField("orden", default=0)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "campo de prematrícula"
        verbose_name_plural = "campos de prematrícula"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class Prematricula(models.Model):
    """Expediente de prematrícula de un aspirante otorgado (RF-065 a RF-072).

    No pasar la prematrícula no hace perder la plaza: no hay renuncia, y
    "rechazar" significa pedir correcciones.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        BORRADOR = "borrador", "Borrador"
        COMPLETADA = "completada", "Completada"
        CON_CORRECCIONES = "con_correcciones", "Con correcciones"
        APROBADA = "aprobada", "Aprobada"
        INCOMPLETA = "incompleta", "Incompleta"

    periodo = models.ForeignKey(PeriodoPrematricula, verbose_name="período", on_delete=models.PROTECT, related_name="prematriculas")
    resultado = models.OneToOneField(
        "otorgamiento.ResultadoOtorgamiento", verbose_name="plaza otorgada", on_delete=models.PROTECT, related_name="prematricula"
    )
    aspirante = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="aspirante", on_delete=models.PROTECT, related_name="prematriculas")
    estado = models.CharField("estado", max_length=16, choices=Estado.choices, default=Estado.PENDIENTE)
    created_at = models.DateTimeField("creada", auto_now_add=True)
    updated_at = models.DateTimeField("actualizada", auto_now=True)
    enviada_at = models.DateTimeField("enviada", null=True, blank=True)
    fecha_aprobacion = models.DateTimeField("fecha de aprobación", null=True, blank=True)
    aprobado_por = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="aprobada por", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        verbose_name = "prematrícula"
        verbose_name_plural = "prematrículas"
        ordering = ["resultado__carrera", "resultado__entidad", "aspirante__last_name", "aspirante__first_name"]

    def __str__(self):
        return f"Prematrícula de {self.resultado.aspirante_nombre}"

    @property
    def oferta(self):
        return self.resultado.otorgada.oferta


class ElementoPrematricula(models.Model):
    """Un elemento del expediente, revisado por separado (pendiente / aprobado / rechazado).

    Es un campo dinámico (`campo`) o un documento del perfil reutilizado
    (`tipo_documento`: CI anverso, CI reverso, certificación).
    """

    class Revision(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de revisión"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"

    prematricula = models.ForeignKey(Prematricula, verbose_name="prematrícula", on_delete=models.CASCADE, related_name="elementos")
    campo = models.ForeignKey(CampoPrematricula, verbose_name="campo", null=True, blank=True, on_delete=models.PROTECT, related_name="elementos")
    tipo_documento = models.ForeignKey(
        "aspirantes.TipoDocumento", verbose_name="documento del perfil", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    valor_texto = models.TextField("valor", blank=True)
    revision = models.CharField("revisión", max_length=10, choices=Revision.choices, default=Revision.PENDIENTE)
    observacion = models.TextField("observación", blank=True)
    revisado_por = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="revisado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    revisado_at = models.DateTimeField("revisado", null=True, blank=True)
    # Versión del documento del perfil que se revisó (para saber si se sustituyó después).
    documento_revisado = models.ForeignKey(
        "aspirantes.DocumentoAspirante", verbose_name="versión revisada", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "elemento de prematrícula"
        verbose_name_plural = "elementos de prematrícula"
        constraints = [
            models.CheckConstraint(
                condition=(Q(campo__isnull=False) & Q(tipo_documento__isnull=True)) | (Q(campo__isnull=True) & Q(tipo_documento__isnull=False)),
                name="elemento_campo_o_documento",
            ),
            models.UniqueConstraint(fields=["prematricula", "campo"], condition=Q(campo__isnull=False), name="elemento_campo_unico"),
            models.UniqueConstraint(fields=["prematricula", "tipo_documento"], condition=Q(tipo_documento__isnull=False), name="elemento_documento_unico"),
        ]

    def __str__(self):
        return self.nombre

    @property
    def nombre(self) -> str:
        return self.campo.nombre if self.campo_id else self.tipo_documento.nombre


def ruta_archivo(archivo, nombre):
    extension = nombre.rsplit(".", 1)[-1].lower()
    return f"prematricula/{archivo.elemento.prematricula.aspirante_id}/{uuid.uuid4().hex}.{extension}"


class ArchivoPrematricula(models.Model):
    """Versión de un archivo de un campo de prematrícula. La vigente es la única con `vigente=True`."""

    elemento = models.ForeignKey(ElementoPrematricula, verbose_name="elemento", on_delete=models.CASCADE, related_name="archivos")
    version = models.PositiveSmallIntegerField("versión")
    vigente = models.BooleanField("vigente", default=True)
    archivo = models.FileField("archivo", upload_to=ruta_archivo)
    nombre_original = models.CharField("nombre original", max_length=255)
    formato = models.CharField("formato", max_length=4)
    tamano = models.PositiveIntegerField("tamaño (bytes)")
    subido_at = models.DateTimeField("subido", auto_now_add=True)

    class Meta:
        verbose_name = "archivo de prematrícula"
        verbose_name_plural = "archivos de prematrícula"
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(fields=["elemento", "version"], name="archivo_prematricula_version_unica"),
            models.UniqueConstraint(fields=["elemento"], condition=Q(vigente=True), name="archivo_prematricula_un_vigente"),
        ]
