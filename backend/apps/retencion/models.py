from django.conf import settings
from django.db import models


class RetencionEjecutada(models.Model):
    """Registro de cada ejecución de la política de retención (RG-028), automática o manual.

    Complementa el log de auditoría con los totales de la ejecución.
    """

    fecha = models.DateTimeField("fecha", auto_now_add=True)
    ejecutada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="ejecutada por", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    automatica = models.BooleanField("automática", default=False)
    aspirantes_anonimizados = models.PositiveIntegerField("aspirantes anonimizados", default=0)
    intereses_anonimizados = models.PositiveIntegerField("expresiones de interés anonimizadas", default=0)
    documentos_eliminados = models.PositiveIntegerField("archivos eliminados", default=0)
    espacio_liberado_mb = models.DecimalField("espacio liberado (MB)", max_digits=12, decimal_places=2, default=0)
    duracion_segundos = models.DecimalField("duración (segundos)", max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "ejecución de la retención"
        verbose_name_plural = "ejecuciones de la retención"
        ordering = ["-fecha"]

    def __str__(self):
        return f"Retención {self.fecha:%Y-%m-%d %H:%M} ({'automática' if self.automatica else 'manual'})"
