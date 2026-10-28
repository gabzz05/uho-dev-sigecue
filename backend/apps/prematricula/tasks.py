from celery import shared_task

from . import services


@shared_task
def avisos_y_cierre_prematricula():
    """Diaria: aviso de apertura, recordatorios a 5 y 1 días (RF-070) y paso a Incompleta tras el cierre."""
    return services.tarea_diaria()
