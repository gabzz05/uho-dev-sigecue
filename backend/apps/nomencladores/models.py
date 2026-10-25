"""Catálogos del sistema (RF-001 a RF-006, RE-005).

Todos se pueden activar y desactivar. Las relaciones usan PROTECT: un
registro en uso no se puede borrar, solo desactivar.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.core.models import ModeloActivable, ModeloConFechas
from apps.core.storage import almacenamiento_publico


class Municipio(ModeloActivable):
    nombre = models.CharField("nombre", max_length=80)
    provincia = models.CharField("provincia", max_length=80, default="Holguín")

    class Meta:
        verbose_name = "municipio"
        verbose_name_plural = "municipios"
        ordering = ["nombre"]
        constraints = [models.UniqueConstraint(fields=["nombre", "provincia"], name="municipio_unico")]

    def __str__(self):
        return self.nombre


class EntidadBase(ModeloActivable, ModeloConFechas):
    """Datos comunes de las entidades que ofertan carreras."""

    nombre = models.CharField("nombre", max_length=150)
    codigo = models.CharField("código", max_length=20, unique=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    email = models.EmailField("email institucional", blank=True)

    class Meta:
        abstract = True
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Facultad(EntidadBase):
    descripcion = models.TextField("descripción", blank=True)
    decano = models.CharField("decano(a)", max_length=150, blank=True)
    municipio = models.ForeignKey(Municipio, verbose_name="municipio", on_delete=models.PROTECT, related_name="facultades")
    imagen = models.ImageField("imagen", upload_to="facultades/", storage=almacenamiento_publico, null=True, blank=True)

    class Meta(EntidadBase.Meta):
        verbose_name = "facultad"
        verbose_name_plural = "facultades"


class CumFum(EntidadBase):
    class Tipo(models.TextChoices):
        CUM = "CUM", "Centro Universitario Municipal"
        FUM = "FUM", "Filial Universitaria Municipal"

    tipo = models.CharField("tipo", max_length=3, choices=Tipo.choices)
    director = models.CharField("director(a)", max_length=150, blank=True)
    municipio = models.ForeignKey(Municipio, verbose_name="municipio", on_delete=models.PROTECT, related_name="cum_fums")
    imagen = models.ImageField("imagen", upload_to="cum_fum/", storage=almacenamiento_publico, null=True, blank=True)

    class Meta(EntidadBase.Meta):
        verbose_name = "CUM/FUM"
        verbose_name_plural = "CUM/FUM"


class Area(ModeloActivable):
    """Área dentro de una Facultad o de un CUM/FUM (RF-005)."""

    nombre = models.CharField("nombre", max_length=150)
    facultad = models.ForeignKey(Facultad, verbose_name="facultad", null=True, blank=True, on_delete=models.PROTECT, related_name="areas")
    cum_fum = models.ForeignKey(CumFum, verbose_name="CUM/FUM", null=True, blank=True, on_delete=models.PROTECT, related_name="areas")

    class Meta:
        verbose_name = "área"
        verbose_name_plural = "áreas"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(
                condition=(Q(facultad__isnull=False) & Q(cum_fum__isnull=True))
                | (Q(facultad__isnull=True) & Q(cum_fum__isnull=False)),
                name="area_una_entidad",
                violation_error_message="El área pertenece a una Facultad o a un CUM/FUM, no a ambos.",
            ),
        ]

    def __str__(self):
        return self.nombre

    @property
    def entidad(self):
        return self.facultad or self.cum_fum


class Departamento(ModeloActivable):
    nombre = models.CharField("nombre", max_length=150)
    area = models.ForeignKey(Area, verbose_name="área", on_delete=models.PROTECT, related_name="departamentos")

    class Meta:
        verbose_name = "departamento"
        verbose_name_plural = "departamentos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Cargo(ModeloActivable):
    nombre = models.CharField("nombre", max_length=100, unique=True)

    class Meta:
        verbose_name = "cargo"
        verbose_name_plural = "cargos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Carrera(ModeloActivable, ModeloConFechas):
    """Catálogo global de carreras (RF-004). Qué entidad la oferta cada año lo define OfertaCarrera."""

    class Modalidad(models.TextChoices):
        POR_ENCUENTRO = "por_encuentro", "Por encuentro"

    nombre = models.CharField("nombre", max_length=150)
    codigo = models.CharField("código", max_length=20, unique=True)
    modalidad = models.CharField("modalidad", max_length=20, choices=Modalidad.choices, default=Modalidad.POR_ENCUENTRO)
    duracion_anios = models.PositiveSmallIntegerField(
        "duración (años)", validators=[MinValueValidator(1), MaxValueValidator(8)]
    )
    descripcion = models.TextField("descripción", blank=True)
    objetivo = models.TextField("objetivo", blank=True)
    perfil_egresado = models.TextField("perfil del egresado", blank=True)
    requisitos = models.TextField("requisitos de ingreso", blank=True)
    imagen = models.ImageField("imagen", upload_to="carreras/", storage=almacenamiento_publico, null=True, blank=True)

    class Meta:
        verbose_name = "carrera"
        verbose_name_plural = "carreras"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
