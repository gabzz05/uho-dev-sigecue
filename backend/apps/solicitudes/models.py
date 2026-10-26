from django.conf import settings
from django.db import models


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
    def editable(self) -> bool:
        """El aspirante puede cambiarla mientras la convocatoria acepte solicitudes (RF-050)."""
        return self.estado in (self.Estado.BORRADOR, self.Estado.PENDIENTE) and self.convocatoria.acepta_solicitudes


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
