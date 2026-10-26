import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

PATRON_ANIO = re.compile(r"^(\d{4})-(\d{4})$")


def validar_anio_academico(valor):
    """Formato `2026-2027`: dos años consecutivos."""
    coincidencia = PATRON_ANIO.match(valor or "")
    if not coincidencia or int(coincidencia.group(2)) != int(coincidencia.group(1)) + 1:
        raise ValidationError("El año académico debe tener la forma 2026-2027 (dos años consecutivos).")


class OfertaCarrera(models.Model):
    """Una carrera ofertada por una entidad en un año académico (modelo conceptual, sección 8).

    La crea la Comisión de Ingreso (RF-027) o la propia entidad con carreras
    del catálogo (RF-028). Los datos del plan de plazas se agregan en su feature.
    """

    carrera = models.ForeignKey("nomencladores.Carrera", verbose_name="carrera", on_delete=models.PROTECT, related_name="ofertas")
    facultad = models.ForeignKey(
        "nomencladores.Facultad", verbose_name="facultad", null=True, blank=True, on_delete=models.PROTECT, related_name="ofertas"
    )
    cum_fum = models.ForeignKey(
        "nomencladores.CumFum", verbose_name="CUM/FUM", null=True, blank=True, on_delete=models.PROTECT, related_name="ofertas"
    )
    anio_academico = models.CharField("año académico", max_length=9, validators=[validar_anio_academico], db_index=True)
    # True si la asignó la Comisión de Ingreso: la entidad no puede quitarla (RF-028).
    asignada_por_ci = models.BooleanField("asignada por la Comisión de Ingreso", default=False)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="creada por", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField("creada", auto_now_add=True)

    class Meta:
        verbose_name = "oferta de carrera"
        verbose_name_plural = "oferta de carreras"
        ordering = ["carrera__nombre"]
        constraints = [
            models.CheckConstraint(
                condition=(Q(facultad__isnull=False) & Q(cum_fum__isnull=True))
                | (Q(facultad__isnull=True) & Q(cum_fum__isnull=False)),
                name="oferta_una_entidad",
            ),
            models.UniqueConstraint(
                fields=["carrera", "facultad", "anio_academico"],
                condition=Q(facultad__isnull=False),
                name="oferta_unica_facultad",
            ),
            models.UniqueConstraint(
                fields=["carrera", "cum_fum", "anio_academico"],
                condition=Q(cum_fum__isnull=False),
                name="oferta_unica_cum_fum",
            ),
        ]

    def __str__(self):
        return f"{self.carrera} — {self.entidad} ({self.anio_academico})"

    @property
    def entidad(self):
        return self.facultad or self.cum_fum

    @property
    def municipio(self):
        return self.entidad.municipio
