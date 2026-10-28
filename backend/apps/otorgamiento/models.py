from django.conf import settings
from django.db import models


class Otorgamiento(models.Model):
    """Otorgamiento de plazas de una convocatoria (sección 5.9). Uno por convocatoria.

    Lo genera la Secretaria General una sola vez; el Jefe CI lo revisa, ajusta y
    aprueba; el Vicerrector lo revisa, ajusta y, al aprobar, lo publica. Los
    resultados son un snapshot: se calculan al generar y con cada ajuste, y al
    publicar quedan congelados. No se recalculan leyendo las solicitudes actuales.
    """

    class Estado(models.TextChoices):
        REVISION_CI = "revision_ci", "Revisión del Jefe CI"
        APROBACION = "aprobacion", "Aprobación del Vicerrector"
        PUBLICADO = "publicado", "Publicado"

    convocatoria = models.OneToOneField(
        "convocatorias.ConvocatoriaSolicitud", verbose_name="convocatoria", on_delete=models.PROTECT, related_name="otorgamiento"
    )
    estado = models.CharField("estado", max_length=12, choices=Estado.choices, default=Estado.REVISION_CI)
    # Plazas disponibles por oferta al generar ({oferta_id: plazas}): plan menos lo ya otorgado en convocatorias anteriores.
    capacidad = models.JSONField("plazas disponibles por oferta", default=dict)
    # Elegibles, no elegibles y motivos al generar (lo que vio y confirmó la Secretaria General).
    resumen = models.JSONField("resumen de elegibilidad", default=dict)
    segunda_convocatoria = models.BooleanField("habrá segunda convocatoria", null=True, blank=True)
    generado_por = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="generado por", null=True, on_delete=models.SET_NULL, related_name="+")
    generado_at = models.DateTimeField("generado", auto_now_add=True)
    aprobado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="aprobado por el Jefe CI", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    aprobado_at = models.DateTimeField("aprobado por el Jefe CI el", null=True, blank=True)
    publicado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="publicado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    publicado_at = models.DateTimeField("publicado", null=True, blank=True)
    # Último día en que el listado se ve en la landing: el cierre de la prematrícula
    # (lo fija el feature de prematrícula). Vacío = visible. Después sigue disponible
    # para los usuarios internos autorizados.
    publico_hasta = models.DateField("visible en la landing hasta", null=True, blank=True)

    class Meta:
        verbose_name = "otorgamiento"
        verbose_name_plural = "otorgamientos"
        ordering = ["-generado_at"]

    def __str__(self):
        return f"Otorgamiento de {self.convocatoria}"

    @property
    def publicado(self) -> bool:
        return self.estado == self.Estado.PUBLICADO


class ResultadoOtorgamiento(models.Model):
    """Snapshot del resultado de un aspirante: con qué índice y en qué posición entró, y qué obtuvo.

    Hay una fila por solicitud confirmada de la convocatoria. Las no elegibles
    llevan `motivo_exclusion` y no tienen posición. `opciones` guarda las
    carreras pedidas tal como estaban al generar.
    """

    class Tipo(models.TextChoices):
        AUTOMATICA = "automatica", "Automática"
        MANUAL = "manual", "Manual"

    otorgamiento = models.ForeignKey(Otorgamiento, verbose_name="otorgamiento", on_delete=models.CASCADE, related_name="resultados")
    solicitud = models.ForeignKey("solicitudes.Solicitud", verbose_name="solicitud", on_delete=models.PROTECT, related_name="resultados")
    aspirante = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="aspirante", on_delete=models.PROTECT, related_name="+")
    aspirante_nombre = models.CharField("aspirante", max_length=301)
    indice_utilizado = models.DecimalField("índice utilizado", max_digits=5, decimal_places=2, null=True, blank=True)
    confirmada_at = models.DateTimeField("solicitud confirmada", null=True, blank=True)
    posicion_ranking = models.PositiveIntegerField("posición en el ranking", null=True, blank=True)
    motivo_exclusion = models.CharField("motivo de exclusión", max_length=255, blank=True)
    opciones = models.JSONField("opciones solicitadas", default=list)
    # Lo otorgado (vacío = no seleccionado). Se guardan también los textos por si cambian los nomencladores.
    otorgada = models.ForeignKey(
        "solicitudes.SolicitudCarrera", verbose_name="opción otorgada", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    carrera = models.CharField("carrera otorgada", max_length=150, blank=True)
    entidad = models.CharField("entidad", max_length=150, blank=True)
    prioridad = models.PositiveSmallIntegerField("prioridad otorgada", null=True, blank=True)
    tipo = models.CharField("tipo de asignación", max_length=10, choices=Tipo.choices, blank=True)

    class Meta:
        verbose_name = "resultado del otorgamiento"
        verbose_name_plural = "resultados del otorgamiento"
        ordering = ["otorgamiento", models.F("posicion_ranking").asc(nulls_last=True), "aspirante_nombre"]
        constraints = [
            models.UniqueConstraint(fields=["otorgamiento", "solicitud"], name="resultado_unico_por_solicitud"),
        ]

    def __str__(self):
        return f"{self.aspirante_nombre}: {self.carrera or 'no seleccionado'}"

    @property
    def elegible(self) -> bool:
        return not self.motivo_exclusion


class AjusteOtorgamiento(models.Model):
    """Edición manual del Jefe CI o del Vicerrector, con justificación (decisión del cliente sobre RF-058/059).

    - `otorgar`: fija al aspirante en una de sus opciones; si tenía otra, la pierde.
    - `quitar`: le impide esa opción; el reparto le da, si alcanza, la siguiente.

    Tras cada ajuste el reparto se recalcula: primero los ajustes vigentes y
    después el algoritmo por orden de ranking cubre las vacantes (cascadas).
    """

    class Tipo(models.TextChoices):
        OTORGAR = "otorgar", "Otorgar"
        QUITAR = "quitar", "Quitar"

    otorgamiento = models.ForeignKey(Otorgamiento, verbose_name="otorgamiento", on_delete=models.CASCADE, related_name="ajustes")
    resultado = models.ForeignKey(ResultadoOtorgamiento, verbose_name="aspirante", on_delete=models.CASCADE, related_name="ajustes")
    tipo = models.CharField("tipo", max_length=8, choices=Tipo.choices)
    opcion = models.ForeignKey("solicitudes.SolicitudCarrera", verbose_name="opción", on_delete=models.PROTECT, related_name="+")
    justificacion = models.TextField("justificación")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="usuario", null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField("fecha", auto_now_add=True)
    # Lo que cambió en el reparto al aplicarlo: [{resultado, aspirante, antes, despues}].
    cambios = models.JSONField("cambios en el reparto", default=list)
    activo = models.BooleanField("vigente", default=True)
    anulado_por = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="anulado por", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    anulado_at = models.DateTimeField("anulado", null=True, blank=True)
    justificacion_anulacion = models.TextField("motivo de la anulación", blank=True)

    class Meta:
        verbose_name = "ajuste del otorgamiento"
        verbose_name_plural = "ajustes del otorgamiento"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.opcion} a {self.resultado.aspirante_nombre}"
