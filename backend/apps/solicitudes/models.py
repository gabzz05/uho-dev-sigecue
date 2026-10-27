from django.conf import settings
from django.db import models
from django.db.models import Q


class Solicitud(models.Model):
    """Solicitud de matrícula de un aspirante en una convocatoria (RF-047 a RF-051).

    Una por aspirante y convocatoria. Tres fechas distintas: cuándo creó el
    borrador (`created_at`), cuándo la confirmó oficialmente (`confirmada_at`,
    desempate del otorgamiento) y cuándo cambió por última vez su selección
    (`modificada_at`). Con la convocatoria cerrada queda congelada.
    """

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        PENDIENTE = "pendiente", "Pendiente"
        EN_REVISION = "en_revision", "En revisión"
        OBSERVADA = "observada", "Observada"
        OTORGADA = "otorgada", "Otorgada"
        NO_SELECCIONADO = "no_seleccionado", "No seleccionado"

    aspirante = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="aspirante", on_delete=models.CASCADE, related_name="solicitudes")
    convocatoria = models.ForeignKey(
        "convocatorias.ConvocatoriaSolicitud", verbose_name="convocatoria", on_delete=models.PROTECT, related_name="solicitudes"
    )
    estado = models.CharField("estado", max_length=16, choices=Estado.choices, default=Estado.BORRADOR)
    created_at = models.DateTimeField("creada", auto_now_add=True)
    confirmada_at = models.DateTimeField("confirmada", null=True, blank=True)
    modificada_at = models.DateTimeField("última modificación", null=True, blank=True)
    # Una observación que afecta la elegibilidad anuló el índice validado: hasta
    # que una entidad lo vuelva a validar, el expediente está pendiente de revisión documental.
    revision_documental_pendiente = models.BooleanField("revisión documental pendiente", default=False)

    class Meta:
        verbose_name = "solicitud"
        verbose_name_plural = "solicitudes"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["aspirante", "convocatoria"], name="solicitud_unica_por_convocatoria"),
        ]

    def __str__(self):
        return f"Solicitud de {self.aspirante.nombre_completo} ({self.convocatoria})"

    @property
    def confirmada(self) -> bool:
        return self.estado != self.Estado.BORRADOR

    @property
    def editable(self) -> bool:
        """El aspirante puede cambiar su selección mientras la convocatoria acepte solicitudes (RF-050)."""
        sin_resultado = self.estado not in (self.Estado.OTORGADA, self.Estado.NO_SELECCIONADO)
        return sin_resultado and self.convocatoria.acepta_solicitudes


class SolicitudCarrera(models.Model):
    """Una carrera elegida, en una entidad concreta, con su prioridad (1 = mayor)."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        OTORGADA = "otorgada", "Otorgada"
        NO_SELECCIONADA = "no_seleccionada", "No seleccionada"

    solicitud = models.ForeignKey(Solicitud, verbose_name="solicitud", on_delete=models.CASCADE, related_name="carreras")
    oferta = models.ForeignKey("oferta.OfertaCarrera", verbose_name="oferta", on_delete=models.PROTECT, related_name="solicitudes")
    prioridad = models.PositiveSmallIntegerField("prioridad")
    estado = models.CharField("estado", max_length=16, choices=Estado.choices, default=Estado.PENDIENTE)

    class Meta:
        verbose_name = "carrera solicitada"
        verbose_name_plural = "carreras solicitadas"
        ordering = ["solicitud", "prioridad"]
        constraints = [
            models.UniqueConstraint(fields=["solicitud", "oferta"], name="solicitud_oferta_unica"),
            models.UniqueConstraint(fields=["solicitud", "prioridad"], name="solicitud_prioridad_unica"),
        ]

    def __str__(self):
        return f"{self.prioridad}. {self.oferta}"


class Observacion(models.Model):
    """Observación de una entidad sobre un elemento corregible de la solicitud (RF-055).

    Apunta siempre a algo que el aspirante puede corregir: un documento, el
    índice, el centro de trabajo o la foto. Mientras no esté RESUELTA, la
    solicitud completa queda fuera del ranking del otorgamiento.
    """

    class Objetivo(models.TextChoices):
        DOCUMENTO = "documento", "Documento"
        INDICE = "indice", "Índice académico"
        CENTRO_TRABAJO = "centro_trabajo", "Centro de trabajo"
        FOTO = "foto", "Foto"

    class Estado(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        CORREGIDA = "corregida", "Corregida"
        RESUELTA = "resuelta", "Resuelta"
        REABIERTA = "reabierta", "Reabierta"

    PENDIENTES_DE_CORREGIR = (Estado.ABIERTA, Estado.REABIERTA)
    NO_RESUELTAS = (Estado.ABIERTA, Estado.CORREGIDA, Estado.REABIERTA)

    solicitud = models.ForeignKey(Solicitud, verbose_name="solicitud", on_delete=models.CASCADE, related_name="observaciones")
    # Entidad autora; las dos vacías si la hizo un rol global.
    facultad = models.ForeignKey(
        "nomencladores.Facultad", verbose_name="facultad", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    cum_fum = models.ForeignKey(
        "nomencladores.CumFum", verbose_name="CUM/FUM", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="autor", null=True, on_delete=models.SET_NULL, related_name="+")
    objetivo = models.CharField("elemento observado", max_length=16, choices=Objetivo.choices)
    tipo_documento = models.ForeignKey(
        "aspirantes.TipoDocumento", verbose_name="documento", null=True, blank=True, on_delete=models.PROTECT, related_name="observaciones"
    )
    texto = models.TextField("observación")
    afecta_elegibilidad = models.BooleanField("afecta la elegibilidad", default=False)
    estado = models.CharField("estado", max_length=10, choices=Estado.choices, default=Estado.ABIERTA)
    created_at = models.DateTimeField("creada", auto_now_add=True)
    updated_at = models.DateTimeField("actualizada", auto_now=True)
    corregida_at = models.DateTimeField("corregida", null=True, blank=True)
    resuelta_at = models.DateTimeField("resuelta", null=True, blank=True)
    resuelta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="resuelta por", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        verbose_name = "observación"
        verbose_name_plural = "observaciones"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(Q(objetivo="documento") & Q(tipo_documento__isnull=False))
                | (~Q(objetivo="documento") & Q(tipo_documento__isnull=True)),
                name="observacion_documento_con_tipo",
            ),
            models.CheckConstraint(condition=Q(facultad__isnull=True) | Q(cum_fum__isnull=True), name="observacion_una_entidad"),
        ]

    def __str__(self):
        return f"{self.elemento} ({self.get_estado_display()})"

    @property
    def elemento(self) -> str:
        return self.tipo_documento.nombre if self.tipo_documento_id else self.get_objetivo_display()

    @property
    def entidad(self):
        return self.facultad or self.cum_fum


class EventoHistorial(models.Model):
    """Historial del expediente de un aspirante (RF-054).

    Cambios de la selección de carreras al guardar, sustituciones de documentos,
    datos del perfil, validación del índice y ciclo de las observaciones.
    `antes`/`despues` guardan los valores tal como estaban.
    """

    class Tipo(models.TextChoices):
        SELECCION = "seleccion", "Selección de carreras"
        CONFIRMACION = "confirmacion", "Confirmación"
        DOCUMENTO = "documento", "Documento"
        DATOS = "datos", "Datos del perfil"
        INDICE_VALIDADO = "indice_validado", "Índice validado"
        OBSERVACION_CREADA = "observacion_creada", "Observación creada"
        OBSERVACION_EDITADA = "observacion_editada", "Observación editada"
        OBSERVACION_CORREGIDA = "observacion_corregida", "Observación corregida"
        OBSERVACION_RESUELTA = "observacion_resuelta", "Observación resuelta"
        OBSERVACION_REABIERTA = "observacion_reabierta", "Observación reabierta"

    aspirante = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="aspirante", on_delete=models.CASCADE, related_name="historial")
    solicitud = models.ForeignKey(Solicitud, verbose_name="solicitud", null=True, blank=True, on_delete=models.CASCADE, related_name="historial")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="usuario", null=True, on_delete=models.SET_NULL, related_name="+")
    tipo = models.CharField("tipo", max_length=24, choices=Tipo.choices)
    descripcion = models.CharField("descripción", max_length=255)
    antes = models.JSONField("antes", null=True, blank=True)
    despues = models.JSONField("después", null=True, blank=True)
    created_at = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        verbose_name = "evento del historial"
        verbose_name_plural = "historial de solicitudes"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.descripcion}"
