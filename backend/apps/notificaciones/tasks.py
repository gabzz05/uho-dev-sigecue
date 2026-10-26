import logging
import smtplib

from celery import shared_task
from django.core.mail import EmailMessage

from apps.configuracion.services import conexion_correo

from .models import Notificacion

logger = logging.getLogger(__name__)


@shared_task
def enviar_correos(ids_notificaciones):
    """Envía por correo el texto de cada notificación. Usa una sola conexión SMTP para el lote
    y continúa si falla algún destinatario. Devuelve cuántos se enviaron."""
    notificaciones = Notificacion.objects.filter(pk__in=ids_notificaciones).select_related("usuario")
    conexion, remitente = conexion_correo()
    enviados = 0
    with conexion:
        for notificacion in notificaciones:
            if not notificacion.usuario.email:
                continue
            try:
                EmailMessage(
                    subject=notificacion.asunto,
                    body=notificacion.cuerpo,
                    from_email=remitente,
                    to=[notificacion.usuario.email],
                    connection=conexion,
                ).send()
                enviados += 1
            except (smtplib.SMTPException, OSError):
                logger.exception("No se pudo enviar el correo de la notificación %s", notificacion.pk)
    return enviados
