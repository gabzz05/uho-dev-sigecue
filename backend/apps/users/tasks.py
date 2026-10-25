import logging

from celery import shared_task
from django.conf import settings

from apps.configuracion.services import enviar_correo

from .models import Usuario
from .services import registro

logger = logging.getLogger(__name__)


@shared_task
def enviar_correo_activacion(usuario_id):
    usuario = Usuario.objects.filter(pk=usuario_id).first()
    if usuario is None:
        return
    enviar_correo(
        "activacion_cuenta",
        [usuario.email],
        {"nombre": usuario.first_name, "enlace": registro.enlace_activacion(usuario), "horas": settings.ACTIVACION_HORAS},
    )


@shared_task
def eliminar_cuentas_no_verificadas():
    borradas = registro.eliminar_no_verificadas()
    if borradas:
        logger.info("Eliminadas %s cuentas de aspirante sin activar.", borradas)
    return borradas
