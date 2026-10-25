import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .models import Usuario
from .services import registro

logger = logging.getLogger(__name__)


@shared_task
def enviar_correo_activacion(usuario_id):
    usuario = Usuario.objects.filter(pk=usuario_id).first()
    if usuario is None:
        return
    contexto = {
        "usuario": usuario,
        "enlace": registro.enlace_activacion(usuario),
        "horas": settings.ACTIVACION_HORAS,
    }
    send_mail(
        subject="SIGECUE — Activa tu cuenta",
        message=render_to_string("emails/activacion.txt", contexto),
        from_email=None,
        recipient_list=[usuario.email],
    )


@shared_task
def eliminar_cuentas_no_verificadas():
    borradas = registro.eliminar_no_verificadas()
    if borradas:
        logger.info("Eliminadas %s cuentas de aspirante sin activar.", borradas)
    return borradas
