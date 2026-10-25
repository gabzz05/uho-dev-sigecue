from django.db import models

from apps.core.models import ModeloActivable, ModeloConFechas

from .catalogo import ACCIONES, MODULOS


class Permiso(models.Model):
    """Una acción sobre un módulo, p. ej. `solicitudes.exportar`."""

    modulo = models.CharField("módulo", max_length=40)
    accion = models.CharField("acción", max_length=20)

    class Meta:
        verbose_name = "permiso"
        verbose_name_plural = "permisos"
        ordering = ["modulo", "accion"]
        constraints = [
            models.UniqueConstraint(fields=["modulo", "accion"], name="permiso_unico"),
        ]

    def __str__(self):
        return self.codigo

    @property
    def codigo(self):
        return f"{self.modulo}.{self.accion}"

    @property
    def modulo_nombre(self):
        return MODULOS.get(self.modulo, (self.modulo,))[0]

    @property
    def accion_nombre(self):
        return ACCIONES.get(self.accion, self.accion)


class Rol(ModeloActivable, ModeloConFechas):
    class Ambito(models.TextChoices):
        GLOBAL = "global", "Global"
        FACULTAD = "facultad", "Local — Facultad"
        CUM_FUM = "cum_fum", "Local — CUM/FUM"
        PROPIO = "propio", "Propio (aspirante)"

    SUPERADMIN = "superadmin"
    ASPIRANTE = "aspirante"

    codigo = models.SlugField("código", max_length=40, unique=True)
    nombre = models.CharField("nombre", max_length=80)
    descripcion = models.TextField("descripción", blank=True)
    ambito = models.CharField("ámbito", max_length=10, choices=Ambito.choices)
    # Los 13 roles de la ERS: no se pueden borrar ni cambiar su código o ámbito.
    es_sistema = models.BooleanField("rol del sistema", default=False, editable=False)
    requiere_area = models.BooleanField(
        "requiere área", default=False, help_text="Los usuarios con este rol se vinculan a un área concreta (Jefes de Área)."
    )
    permisos = models.ManyToManyField(Permiso, verbose_name="permisos", blank=True, related_name="roles")

    class Meta:
        verbose_name = "rol"
        verbose_name_plural = "roles"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def es_global(self):
        return self.ambito == self.Ambito.GLOBAL

    @property
    def es_local(self):
        return self.ambito in (self.Ambito.FACULTAD, self.Ambito.CUM_FUM)
