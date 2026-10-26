from django.conf import settings
from django.db import models


class Notificacion(models.Model):
    """Notificación in-app de un usuario (RF-073, RF-074). El mismo texto se envía por correo."""

    MASIVA = "masiva"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="usuario", on_delete=models.CASCADE, related_name="notificaciones"
    )
    # Código de la plantilla que la originó, o "masiva".
    tipo = models.CharField("tipo", max_length=60)
    asunto = models.CharField("asunto", max_length=200)
    cuerpo = models.TextField("cuerpo")
    leida = models.BooleanField("leída", default=False)
    leida_at = models.DateTimeField("leída el", null=True, blank=True)
    envio = models.ForeignKey(
        "EnvioMasivo", verbose_name="envío masivo", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["usuario", "leida"], name="notificacion_no_leidas")]

    def __str__(self):
        return self.asunto


class EnvioMasivo(models.Model):
    """Registro de un envío masivo (RF-076): a quién, qué y cuántos destinatarios."""

    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="enviado por", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    grupo = models.JSONField("grupo de destinatarios")
    grupo_descripcion = models.CharField("destinatarios", max_length=255)
    asunto = models.CharField("asunto", max_length=200)
    cuerpo = models.TextField("cuerpo")
    por_correo = models.BooleanField("también por correo", default=False)
    destinatarios = models.PositiveIntegerField("número de destinatarios")
    # Entidad desde la que se envió (roles locales); vacía para los globales.
    facultad = models.ForeignKey("nomencladores.Facultad", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    cum_fum = models.ForeignKey("nomencladores.CumFum", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        verbose_name = "envío masivo"
        verbose_name_plural = "envíos masivos"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.asunto
