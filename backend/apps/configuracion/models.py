"""Configuración editable desde el panel (sección 5.1). Solo la modifica el Superadmin.

`ConfiguracionSistema`, `ConfiguracionSMTP` e `IdentidadVisual` son singletons:
siempre una sola fila (pk=1), que se crea con valores por defecto al pedirla.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

from apps.core.fields import CampoCifrado
from apps.core.storage import almacenamiento_publico

validar_color = RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Usa un color hexadecimal, p. ej. #1A3A6B.")


class Singleton(models.Model):
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="actualizado por", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    updated_at = models.DateTimeField("modificado", auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def actual(cls):
        instancia, _ = cls.objects.get_or_create(pk=1)
        return instancia


# Los valores iniciales salen del .env (LOGIN_MAX_INTENTOS / LOGIN_BLOQUEO_MINUTOS).
def intentos_por_defecto():
    return getattr(settings, "LOGIN_MAX_INTENTOS", 5)


def bloqueo_por_defecto():
    return getattr(settings, "LOGIN_BLOQUEO_MINUTOS", 15)


class ConfiguracionSistema(Singleton):
    """Parámetros del proceso (RF-007, RF-008)."""

    max_carreras_aspirante = models.PositiveSmallIntegerField(
        "máximo de carreras por aspirante", default=5, validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    # RG-028: años que se conservan los datos personales antes de anonimizarlos.
    retencion_anios = models.PositiveSmallIntegerField(
        "retención de datos (años)", default=2, validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text="No seleccionados, expresiones de interés y versiones antiguas de documentos.",
    )
    retencion_otorgados_anios = models.PositiveSmallIntegerField(
        "retención de datos de otorgados (años)", default=5, validators=[MinValueValidator(1), MaxValueValidator(30)],
        help_text="Conservación ampliada de quienes obtuvieron plaza (reclamaciones, prematrícula, consultas).",
    )
    login_max_intentos = models.PositiveSmallIntegerField(
        "intentos de inicio de sesión antes del bloqueo",
        default=intentos_por_defecto,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
    )
    login_bloqueo_minutos = models.PositiveSmallIntegerField(
        "minutos de bloqueo",
        default=bloqueo_por_defecto,
        validators=[MinValueValidator(1), MaxValueValidator(1440)],
    )

    class Meta:
        verbose_name = "parámetros del sistema"
        verbose_name_plural = "parámetros del sistema"


class ConfiguracionSMTP(Singleton):
    """Servidor de correo (RF-009, RE-010). Si `activo` es falso se usan las variables de entorno."""

    activo = models.BooleanField("usar esta configuración", default=False)
    host = models.CharField("servidor", max_length=255, blank=True)
    puerto = models.PositiveIntegerField("puerto", default=587, validators=[MaxValueValidator(65535)])
    usuario = models.CharField("usuario", max_length=255, blank=True)
    # Cifrada (AES-256): el sistema necesita leerla para autenticarse. La API nunca la devuelve.
    password = CampoCifrado("contraseña", blank=True)
    usar_tls = models.BooleanField("usar STARTTLS", default=True)
    usar_ssl = models.BooleanField("usar SSL/TLS implícito", default=False)
    remitente = models.CharField("remitente por defecto", max_length=255, blank=True)

    class Meta:
        verbose_name = "configuración SMTP"
        verbose_name_plural = "configuración SMTP"


class IdentidadVisual(Singleton):
    """Colores, escudo y nombre institucional (RE-001). Los colores se aplican en el frontend."""

    nombre_institucion = models.CharField("nombre de la institución", max_length=150, default="Universidad de Holguín")
    color_primario = models.CharField("color primario", max_length=7, default="#1A3A6B", validators=[validar_color])
    color_primario_claro = models.CharField(
        "color primario claro", max_length=7, default="#2E6DB4", validators=[validar_color]
    )
    color_acento = models.CharField("color de acento", max_length=7, default="#C8102E", validators=[validar_color])
    escudo = models.ImageField("escudo", upload_to="identidad/", storage=almacenamiento_publico, null=True, blank=True)

    class Meta:
        verbose_name = "identidad visual"
        verbose_name_plural = "identidad visual"


class PlantillaCorreo(models.Model):
    """Texto editable de un correo del sistema (RF-011). Qué plantillas existen lo define el código."""

    codigo = models.SlugField("código", max_length=60, unique=True)
    asunto = models.CharField("asunto", max_length=200)
    cuerpo = models.TextField("cuerpo")
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="actualizado por", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    updated_at = models.DateTimeField("modificado", auto_now=True)

    class Meta:
        verbose_name = "plantilla de correo"
        verbose_name_plural = "plantillas de correo"
        ordering = ["codigo"]

    def __str__(self):
        return self.codigo
