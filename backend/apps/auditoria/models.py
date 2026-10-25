from django.conf import settings
from django.db import models


class LogInmutableError(Exception):
    """Se intentó modificar o borrar un registro de auditoría."""


class LogAuditoriaQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise LogInmutableError("Los registros de auditoría no se pueden modificar.")

    def delete(self):
        raise LogInmutableError("Los registros de auditoría no se pueden borrar.")


class LogAuditoria(models.Model):
    """Registro de una acción de usuario (RG-010). Solo se puede crear."""

    class Resultado(models.TextChoices):
        EXITO = "exito", "Éxito"
        ERROR = "error", "Error"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    # Copia del nombre de usuario: el registro conserva quién fue aunque el usuario se borre.
    usuario_nombre = models.CharField("nombre de usuario", max_length=150, blank=True)
    accion = models.CharField("acción", max_length=150)
    modulo = models.CharField("módulo", max_length=60, db_index=True)
    entidad_afectada = models.CharField("entidad afectada", max_length=60, blank=True)
    entidad_id = models.CharField("id de la entidad", max_length=64, blank=True)
    metodo = models.CharField("método HTTP", max_length=10, blank=True)
    ruta = models.CharField("ruta", max_length=255, blank=True)
    ip = models.GenericIPAddressField("dirección IP", null=True, blank=True)
    resultado = models.CharField("resultado", max_length=10, choices=Resultado.choices)
    codigo_http = models.PositiveSmallIntegerField("código HTTP", null=True, blank=True)
    detalle = models.JSONField("detalle", default=dict, blank=True)
    created_at = models.DateTimeField("fecha y hora", auto_now_add=True, db_index=True)

    objects = LogAuditoriaQuerySet.as_manager()

    class Meta:
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.usuario_nombre or 'anónimo'} {self.accion}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise LogInmutableError("Los registros de auditoría no se pueden modificar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise LogInmutableError("Los registros de auditoría no se pueden borrar.")
