import uuid
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import ErrorDeNegocio
from apps.roles.models import Rol
from apps.users.models import Usuario

_SALT_ACTIVACION = "users.activacion"


def generar_token_activacion(usuario):
    return signing.dumps({"u": usuario.pk}, salt=_SALT_ACTIVACION)


def enlace_activacion(usuario):
    return f"{settings.FRONTEND_URL}/activar?token={generar_token_activacion(usuario)}"


@transaction.atomic
def registrar_aspirante(*, nombre, apellidos, ci, email, celular, password):
    """Crea la cuenta del aspirante (RF-013/RF-044) y envía el correo de activación (RF-045)."""
    from apps.users.tasks import enviar_correo_activacion

    usuario = Usuario(
        username=f"asp_{uuid.uuid4().hex[:16]}",
        first_name=nombre,
        last_name=apellidos,
        ci=ci,
        email=email,
        celular=celular,
        rol=Rol.objects.get(codigo=Rol.ASPIRANTE),
        email_verificado=False,
        privacidad_aceptada_at=timezone.now(),
    )
    usuario.set_password(password)
    usuario.save()
    transaction.on_commit(lambda: enviar_correo_activacion.delay(usuario.pk))
    return usuario


def activar_cuenta(token):
    try:
        datos = signing.loads(token, salt=_SALT_ACTIVACION, max_age=timedelta(hours=settings.ACTIVACION_HORAS))
    except signing.SignatureExpired:
        raise ErrorDeNegocio("El enlace de activación caducó. Vuelve a registrarte.")
    except signing.BadSignature:
        raise ErrorDeNegocio("El enlace de activación no es válido.")

    usuario = Usuario.objects.filter(pk=datos["u"]).first()
    if usuario is None:
        raise ErrorDeNegocio("La cuenta ya no existe. Vuelve a registrarte.")
    if not usuario.email_verificado:
        usuario.email_verificado = True
        usuario.save(update_fields=["email_verificado"])
    return usuario


def eliminar_no_verificadas():
    """Borra cuentas de aspirante sin activar pasado el plazo (RF-045). Devuelve cuántas."""
    limite = timezone.now() - timedelta(hours=settings.ACTIVACION_HORAS)
    pendientes = Usuario.objects.filter(
        rol__codigo=Rol.ASPIRANTE, email_verificado=False, date_joined__lt=limite
    )
    borradas, _ = pendientes.delete()
    return borradas
