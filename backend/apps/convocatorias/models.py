from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.oferta.models import validar_anio_academico


class ConvocatoriaSolicitud(models.Model):
    """Convocatoria oficial de solicitud de matrícula (RF-040 a RF-043).

    `numero` distingue la primera, segunda... convocatoria de un mismo año
    (RF-062). Sin entidades seleccionadas, aplica a todas las que tienen
    plazas en el plan de plazas publicado.
    """

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        ABIERTA = "abierta", "Abierta"
        CERRADA = "cerrada", "Cerrada"

    anio_academico = models.CharField("año académico", max_length=9, validators=[validar_anio_academico], db_index=True)
    numero = models.PositiveSmallIntegerField("número de convocatoria", default=1)
    fecha_inicio = models.DateField("fecha de inicio")
    fecha_cierre = models.DateField("fecha de cierre")
    mensaje_publico = models.TextField("mensaje público", blank=True)
    estado = models.CharField("estado", max_length=10, choices=Estado.choices, default=Estado.BORRADOR)
    facultades = models.ManyToManyField("nomencladores.Facultad", verbose_name="facultades", blank=True, related_name="+")
    cum_fums = models.ManyToManyField("nomencladores.CumFum", verbose_name="CUM/FUM", blank=True, related_name="+")
    interesados_notificados = models.PositiveIntegerField("interesados notificados", null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="creada por", null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField("creada", auto_now_add=True)

    class Meta:
        verbose_name = "convocatoria de solicitud"
        verbose_name_plural = "convocatorias de solicitud"
        ordering = ["-anio_academico", "-numero"]
        constraints = [
            models.UniqueConstraint(fields=["anio_academico", "numero"], name="convocatoria_solicitud_unica"),
            models.UniqueConstraint(fields=["estado"], condition=Q(estado="abierta"), name="una_convocatoria_solicitud_abierta"),
            models.CheckConstraint(
                condition=Q(fecha_cierre__gte=F("fecha_inicio")),
                name="convocatoria_solicitud_fechas",
                violation_error_message="La fecha de cierre no puede ser anterior a la de inicio.",
            ),
        ]

    def __str__(self):
        return f"Convocatoria {self.numero} de solicitud {self.anio_academico}"

    @property
    def acepta_solicitudes(self) -> bool:
        """Abierta y con la fecha de hoy dentro de su rango (RF-043)."""
        hoy = timezone.localdate()
        return self.estado == self.Estado.ABIERTA and self.fecha_inicio <= hoy <= self.fecha_cierre

    @property
    def para_todas_las_entidades(self) -> bool:
        return not self.facultades.exists() and not self.cum_fums.exists()
