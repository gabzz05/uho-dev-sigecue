from django.db import models


class ModeloConFechas(models.Model):
    """Base con marcas de creación y última modificación."""

    created_at = models.DateTimeField("creado", auto_now_add=True)
    updated_at = models.DateTimeField("modificado", auto_now=True)

    class Meta:
        abstract = True


class ActivosManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(activo=True)


class ModeloActivable(models.Model):
    """Base para registros que se activan/desactivan en vez de borrarse (RE-005)."""

    activo = models.BooleanField("activo", default=True)

    objects = models.Manager()
    activos = ActivosManager()

    class Meta:
        abstract = True
