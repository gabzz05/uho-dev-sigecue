from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property

from apps.core import crypto
from apps.core.fields import CampoCifrado
from apps.roles.models import Rol


class Usuario(AbstractUser):
    """Usuario del sistema: roles internos y aspirantes.

    - `first_name` / `last_name` son el nombre y los apellidos.
    - Email, CI y celular se guardan cifrados (RG-025). Email y CI llevan
      además un hash para búsqueda y unicidad.
    - Los internos inician sesión con `username`; los aspirantes con su email
      (su `username` se genera automáticamente).
    - `is_active=False` es una cuenta bloqueada por un administrador (RF-017).
      El bloqueo temporal por intentos fallidos (RG-009) usa `bloqueado_hasta`.
    """

    class Origen(models.TextChoices):
        LOCAL = "local", "Local"
        SGU = "sgu", "SGU (auth.uho.edu.cu)"

    email = CampoCifrado("email", blank=True)
    email_hash = models.CharField(max_length=64, unique=True, null=True, editable=False)
    ci = CampoCifrado("carnet de identidad", blank=True)
    ci_hash = models.CharField(max_length=64, unique=True, null=True, editable=False)
    celular = CampoCifrado("celular", blank=True)

    rol = models.ForeignKey(Rol, verbose_name="rol", null=True, blank=True, on_delete=models.PROTECT, related_name="usuarios")
    foto = models.ImageField("foto", upload_to="usuarios/fotos/", null=True, blank=True)
    origen = models.CharField("origen", max_length=10, choices=Origen.choices, default=Origen.LOCAL)

    email_verificado = models.BooleanField("email verificado", default=False)
    privacidad_aceptada_at = models.DateTimeField("política de privacidad aceptada", null=True, blank=True)

    intentos_fallidos = models.PositiveSmallIntegerField("intentos fallidos", default=0)
    bloqueado_hasta = models.DateTimeField("bloqueado hasta", null=True, blank=True)

    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def save(self, *args, **kwargs):
        self.email_hash = crypto.hash_busqueda(self.email) if self.email else None
        self.ci_hash = crypto.hash_busqueda(self.ci) if self.ci else None
        super().save(*args, **kwargs)

    @property
    def nombre_completo(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def es_superadmin(self):
        return self.is_superuser or (self.rol_id is not None and self.rol.codigo == Rol.SUPERADMIN)

    @property
    def es_aspirante(self):
        return self.rol_id is not None and self.rol.codigo == Rol.ASPIRANTE

    @property
    def esta_bloqueado_temporalmente(self):
        return self.bloqueado_hasta is not None and self.bloqueado_hasta > timezone.now()

    @cached_property
    def codigos_permiso(self):
        if self.rol_id is None or not self.rol.activo:
            return frozenset()
        return frozenset(f"{p.modulo}.{p.accion}" for p in self.rol.permisos.all())

    def tiene_permiso(self, modulo, accion):
        if not self.is_active:
            return False
        if self.es_superadmin:
            return True
        return f"{modulo}.{accion}" in self.codigos_permiso
