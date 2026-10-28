from celery import shared_task

from . import services


@shared_task
def aplicar_retencion():
    """Mensual: aplica la política de retención (RG-028)."""
    return services.ejecutar(automatica=True).pk
