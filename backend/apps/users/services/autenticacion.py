from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone
from rest_framework import exceptions
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auditoria import services as auditoria
from apps.core import crypto
from apps.users import sgu
from apps.users.models import Usuario

CREDENCIALES_INVALIDAS = "Usuario o contraseña incorrectos."


class CredencialesInvalidas(exceptions.AuthenticationFailed):
    default_code = "credenciales_invalidas"
    default_detail = CREDENCIALES_INVALIDAS


class CuentaNoDisponible(exceptions.PermissionDenied):
    """Credenciales correctas, pero la cuenta no puede iniciar sesión."""

    default_code = "cuenta_no_disponible"


def _buscar(identificador):
    """Los aspirantes entran con su email; los internos con su nombre de usuario."""
    identificador = identificador.strip()
    if "@" in identificador:
        return Usuario.objects.filter(email_hash=crypto.hash_busqueda(identificador)).first()
    return Usuario.objects.filter(username=identificador).first()


def _verificar_password(usuario, password):
    if usuario.origen == Usuario.Origen.SGU:
        proveedor = sgu.obtener_proveedor()
        return proveedor is not None and proveedor.autenticar(usuario.username, password) is not None
    return usuario.check_password(password)


def _registrar_fallo(usuario, request):
    usuario.intentos_fallidos += 1
    if usuario.intentos_fallidos >= settings.LOGIN_MAX_INTENTOS:
        usuario.bloqueado_hasta = timezone.now() + timedelta(minutes=settings.LOGIN_BLOQUEO_MINUTOS)
        usuario.intentos_fallidos = 0
        auditoria.registrar(
            request=request, usuario=usuario, accion="bloqueo temporal por intentos fallidos",
            modulo="auth", entidad_afectada="usuario", entidad_id=usuario.pk,
            resultado=auditoria.LogAuditoria.Resultado.ERROR,
        )
    usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])


def _comprobar_credenciales(usuario, password, request):
    """Actualiza los contadores de intentos y devuelve la excepción a lanzar, o None."""
    if usuario.esta_bloqueado_temporalmente:
        minutos = max(1, int((usuario.bloqueado_hasta - timezone.now()).total_seconds() // 60) + 1)
        return CuentaNoDisponible(
            f"Demasiados intentos fallidos. Podrás intentarlo de nuevo en {minutos} minuto(s)."
        )

    if not _verificar_password(usuario, password):
        _registrar_fallo(usuario, request)
        return CredencialesInvalidas()

    if usuario.intentos_fallidos or usuario.bloqueado_hasta:
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
    return None


def autenticar(identificador, password, request=None):
    """Valida las credenciales aplicando el bloqueo temporal (RG-009).

    Ante un usuario inexistente o una contraseña errónea el mensaje es el
    mismo, para no revelar qué cuentas existen.
    """
    usuario = _buscar(identificador)
    if usuario is None:
        make_password(password)  # Iguala el tiempo de respuesta con el de un usuario real.
        raise CredencialesInvalidas()

    # El contador se actualiza con la fila bloqueada para que dos intentos
    # simultáneos no se pisen. La excepción se lanza fuera de la transacción
    # para no revertir el contador.
    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().get(pk=usuario.pk)
        error = _comprobar_credenciales(usuario, password, request)
    if error is not None:
        raise error

    if not usuario.is_active:
        raise CuentaNoDisponible("Tu cuenta está bloqueada. Contacta con la administración del sistema.")
    if usuario.es_aspirante and not usuario.email_verificado:
        raise CuentaNoDisponible("Debes activar tu cuenta con el enlace que enviamos a tu correo.")
    return usuario


def emitir_tokens(usuario):
    refresh = RefreshToken.for_user(usuario)
    if settings.SIMPLE_JWT.get("UPDATE_LAST_LOGIN"):
        Usuario.objects.filter(pk=usuario.pk).update(last_login=timezone.now())
    return str(refresh.access_token), str(refresh)


def revocar(refresh):
    """Invalida un refresh token (cierre de sesión). Ignora tokens ya inválidos."""
    try:
        RefreshToken(refresh).blacklist()
    except Exception:
        pass
