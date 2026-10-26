from celery import shared_task
from django.conf import settings

from apps.configuracion.services import enviar_correo
from apps.interes.models import ExpresionInteres
from apps.notificaciones.services import notificar
from apps.roles.models import Rol
from apps.users.models import Usuario

from . import services
from .models import ConvocatoriaSolicitud


@shared_task
def notificar_interesados(convocatoria_id):
    """RF-041: avisa a quienes expresaron interés en la convocatoria de interés del mismo año.

    Una sola vez por persona: si su CI coincide con una cuenta de aspirante,
    notificación in-app + correo a la cuenta; si no, un correo al email que dejó.
    Devuelve cuántas personas se notificaron.
    """
    convocatoria = ConvocatoriaSolicitud.objects.get(pk=convocatoria_id)
    contexto = {
        "anio": convocatoria.anio_academico,
        "fecha_cierre": convocatoria.fecha_cierre.strftime("%d/%m/%Y"),
        "enlace": f"{settings.FRONTEND_URL}/registro",
    }

    personas = {}  # ci_hash -> (nombre, email) del registro más reciente
    for expresion in ExpresionInteres.objects.filter(convocatoria__anio_academico=convocatoria.anio_academico).order_by("created_at"):
        personas[expresion.ci_hash] = (expresion.nombre, expresion.email)

    con_cuenta = Usuario.objects.filter(
        ci_hash__in=personas, rol__codigo=Rol.ASPIRANTE, is_active=True, email_verificado=True
    )
    notificar(con_cuenta, "convocatoria_solicitud_abierta", contexto)

    hashes_con_cuenta = {u.ci_hash for u in con_cuenta}
    emails = {}
    for ci_hash, (nombre, email) in personas.items():
        if ci_hash not in hashes_con_cuenta:
            emails.setdefault(email.lower(), nombre)
    for email, nombre in emails.items():
        enviar_correo("convocatoria_solicitud_abierta", [email], contexto | {"nombre": nombre.split()[0]})

    total = len(hashes_con_cuenta) + len(emails)
    ConvocatoriaSolicitud.objects.filter(pk=convocatoria.pk).update(interesados_notificados=total)
    return total


@shared_task
def cerrar_convocatorias_vencidas():
    return services.cerrar_vencidas()
