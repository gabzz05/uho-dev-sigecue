from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.core import crypto
from apps.core.fields import CampoCifrado
from apps.oferta.models import validar_anio_academico


class ConvocatoriaInteres(models.Model):
    """Convocatoria anual de expresión de interés (RF-026). Una por año académico."""

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        ABIERTA = "abierta", "Abierta"
        CERRADA = "cerrada", "Cerrada"

    anio_academico = models.CharField("año académico", max_length=9, unique=True, validators=[validar_anio_academico])
    fecha_inicio = models.DateField("fecha de inicio")
    fecha_cierre = models.DateField("fecha de cierre")
    mensaje_publico = models.TextField("mensaje público", blank=True)
    estado = models.CharField("estado", max_length=10, choices=Estado.choices, default=Estado.BORRADOR)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="creada por", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField("creada", auto_now_add=True)

    class Meta:
        verbose_name = "convocatoria de interés"
        verbose_name_plural = "convocatorias de interés"
        ordering = ["-anio_academico"]
        constraints = [
            models.CheckConstraint(
                condition=Q(fecha_cierre__gte=F("fecha_inicio")),
                name="convocatoria_interes_fechas",
                violation_error_message="La fecha de cierre no puede ser anterior a la de inicio.",
            ),
            # Solo una convocatoria abierta a la vez.
            models.UniqueConstraint(fields=["estado"], condition=Q(estado="abierta"), name="una_convocatoria_interes_abierta"),
        ]

    def __str__(self):
        return f"Convocatoria de interés {self.anio_academico}"

    @property
    def acepta_interes(self) -> bool:
        """Abierta y con la fecha de hoy dentro de su rango."""
        hoy = timezone.localdate()
        return self.estado == self.Estado.ABIERTA and self.fecha_inicio <= hoy <= self.fecha_cierre

    @property
    def editable(self) -> bool:
        """La oferta se puede modificar mientras no esté cerrada."""
        return self.estado != self.Estado.CERRADA


class ExpresionInteres(models.Model):
    """Interés anónimo (sin registro) de un ciudadano por una oferta (RF-021, RF-022).

    CI, celular y email van cifrados (RG-025). El CI lleva un hash para impedir
    que la misma persona repita el interés por la misma oferta.
    """

    convocatoria = models.ForeignKey(ConvocatoriaInteres, verbose_name="convocatoria", on_delete=models.PROTECT, related_name="expresiones")
    oferta = models.ForeignKey("oferta.OfertaCarrera", verbose_name="oferta", on_delete=models.PROTECT, related_name="expresiones_interes")
    nombre = models.CharField("nombre completo", max_length=200)
    ci = CampoCifrado("carnet de identidad")
    ci_hash = models.CharField(max_length=64, editable=False)
    celular = CampoCifrado("celular")
    email = CampoCifrado("email")
    created_at = models.DateTimeField("fecha", auto_now_add=True, db_index=True)
    # RG-028: sin nombre, CI, celular ni email; se conservan carrera, entidad y fecha para estadísticas.
    anonimizada_at = models.DateTimeField("anonimizada", null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "expresión de interés"
        verbose_name_plural = "expresiones de interés"
        ordering = ["-created_at", "-id"]
        constraints = [
            # RF-022: el mismo CI no repite el interés por la misma oferta (carrera + entidad + año).
            models.UniqueConstraint(fields=["oferta", "ci_hash"], name="interes_unico_por_oferta"),
        ]

    def __str__(self):
        return f"{self.nombre} — {self.oferta}"

    def save(self, *args, **kwargs):
        self.ci_hash = crypto.hash_busqueda(self.ci)
        super().save(*args, **kwargs)
