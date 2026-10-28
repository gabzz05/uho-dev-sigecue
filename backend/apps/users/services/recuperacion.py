"""Recuperación de contraseña por correo.

El token es el de Django (`default_token_generator`): depende del hash de la
contraseña y del último inicio de sesión, así que deja de valer en cuanto se
usa. Caduca a los `PASSWORD_RESET_TIMEOUT` segundos.
"""

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.core import crypto
from apps.core.exceptions import ErrorDeNegocio
from apps.users.models import Usuario

ENLACE_INVALIDO = "El enlace para restablecer la contraseña no es válido o ya caducó. Pide uno nuevo."


def horas_validez():
    return settings.PASSWORD_RESET_TIMEOUT // 3600


def puede_recuperar(usuario):
    """Solo cuentas locales activas con correo. Las del SGU cambian la contraseña allí."""
    if not usuario.is_active or usuario.origen != Usuario.Origen.LOCAL or not usuario.email:
        return False
    return usuario.email_verificado or not usuario.es_aspirante


def enlace_recuperacion(usuario):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    return f"{settings.FRONTEND_URL}/restablecer?uid={uid}&token={default_token_generator.make_token(usuario)}"


def solicitar(email):
    """Envía el enlace si el correo es de una cuenta que puede recuperarse.

    No dice si la cuenta existe: la respuesta al usuario es siempre la misma.
    """
    from apps.users.tasks import enviar_correo_recuperacion

    usuario = Usuario.objects.filter(email_hash=crypto.hash_busqueda(email.strip())).first()
    if usuario is not None and puede_recuperar(usuario):
        transaction.on_commit(lambda: enviar_correo_recuperacion.delay(usuario.pk))


def usuario_del_enlace(uid, token):
    try:
        usuario = Usuario.objects.filter(pk=int(force_str(urlsafe_base64_decode(uid)))).first()
    except (TypeError, ValueError, OverflowError):
        usuario = None
    if usuario is None or not puede_recuperar(usuario) or not default_token_generator.check_token(usuario, token):
        raise ErrorDeNegocio(ENLACE_INVALIDO)
    return usuario


@transaction.atomic
def restablecer(usuario, password):
    """Cambia la contraseña, quita el bloqueo por intentos y cierra las sesiones abiertas."""
    usuario.set_password(password)
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    usuario.save(update_fields=["password", "intentos_fallidos", "bloqueado_hasta"])
    for token in OutstandingToken.objects.filter(user=usuario, blacklistedtoken__isnull=True):
        BlacklistedToken.objects.get_or_create(token=token)
