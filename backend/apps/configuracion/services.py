import logging
import smtplib

from django.conf import settings
from django.core.mail import EmailMessage, get_connection

from apps.core.exceptions import ErrorDeNegocio

from . import plantillas
from .catalogo_plantillas import PLANTILLAS
from .models import ConfiguracionSistema, ConfiguracionSMTP, PlantillaCorreo

logger = logging.getLogger(__name__)

TIMEOUT_SMTP_SEGUNDOS = 10


def parametros():
    """Parámetros del sistema vigentes (RF-007, RF-008)."""
    return ConfiguracionSistema.actual()


def conexion_correo():
    """Conexión y remitente a usar.

    Si el Superadmin activó la configuración SMTP del panel, se usa esa (RE-010);
    si no, la de las variables de entorno.
    """
    smtp = ConfiguracionSMTP.actual()
    if not smtp.activo:
        return get_connection(), settings.DEFAULT_FROM_EMAIL
    conexion = get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=smtp.host,
        port=smtp.puerto,
        username=smtp.usuario,
        password=smtp.password,
        use_tls=smtp.usar_tls,
        use_ssl=smtp.usar_ssl,
        timeout=TIMEOUT_SMTP_SEGUNDOS,
    )
    return conexion, smtp.remitente or settings.DEFAULT_FROM_EMAIL


def texto_plantilla(codigo):
    """Asunto y cuerpo vigentes: los editados en el panel o, si faltan, los del catálogo."""
    plantilla = PlantillaCorreo.objects.filter(codigo=codigo).first()
    if plantilla is not None:
        return plantilla.asunto, plantilla.cuerpo
    return PLANTILLAS[codigo]["asunto"], PLANTILLAS[codigo]["cuerpo"]


def enviar_correo(codigo, destinatarios, contexto):
    """Envía el correo de la plantilla `codigo` con las variables de `contexto`."""
    asunto, cuerpo = texto_plantilla(codigo)
    conexion, remitente = conexion_correo()
    EmailMessage(
        subject=plantillas.renderizar(asunto, contexto),
        body=plantillas.renderizar(cuerpo, contexto),
        from_email=remitente,
        to=list(destinatarios),
        connection=conexion,
    ).send()


def probar_smtp(destinatario):
    """Correo de prueba con la configuración guardada (RF-009)."""
    conexion, remitente = conexion_correo()
    mensaje = EmailMessage(
        subject="SIGECUE — Correo de prueba",
        body="Este es un correo de prueba de SIGECUE. Si lo recibiste, la configuración de correo funciona.",
        from_email=remitente,
        to=[destinatario],
        connection=conexion,
    )
    try:
        mensaje.send()
    except (smtplib.SMTPException, OSError) as exc:
        logger.warning("Fallo la prueba de SMTP: %s", exc)
        raise ErrorDeNegocio(
            f"No se pudo enviar el correo de prueba. Revisa el servidor, el puerto y las credenciales. Detalle: {exc}"
        )
