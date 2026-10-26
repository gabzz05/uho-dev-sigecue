from celery import shared_task

from apps.configuracion.services import enviar_correo

from . import services
from .models import ExpresionInteres


@shared_task
def enviar_confirmacion(expresion_id):
    """Correo "interés registrado" (RF-011). Quien expresó interés no tiene cuenta: solo correo."""
    expresion = ExpresionInteres.objects.select_related("oferta__carrera", "oferta__facultad", "oferta__cum_fum").filter(pk=expresion_id).first()
    if expresion is None:
        return
    enviar_correo(
        "interes_confirmado",
        [expresion.email],
        {
            "nombre": expresion.nombre,
            "carrera": expresion.oferta.carrera.nombre,
            "entidad": str(expresion.oferta.entidad),
            "anio": expresion.oferta.anio_academico,
        },
    )


@shared_task
def cerrar_convocatorias_vencidas():
    return services.cerrar_vencidas()
