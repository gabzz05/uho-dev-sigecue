from django.contrib.auth.models import AbstractUser


class Usuario(AbstractUser):
    """Usuario del sistema (roles internos y aspirantes).

    Se define desde el inicio para que todas las relaciones apunten a él;
    los campos propios (CI, celular, rol, entidad...) se agregan en
    feature/auth-users.
    """

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
