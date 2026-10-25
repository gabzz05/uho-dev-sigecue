import logging

from django.conf import settings

from .models import LogAuditoria

logger = logging.getLogger(__name__)


def obtener_ip(request):
    """IP del cliente. Detrás del proxy inverso se toma la primera de X-Forwarded-For."""
    if getattr(settings, "AUDITORIA_CONFIAR_X_FORWARDED_FOR", False):
        reenviada = request.META.get("HTTP_X_FORWARDED_FOR")
        if reenviada:
            return reenviada.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def registrar(
    *,
    accion,
    modulo,
    resultado=LogAuditoria.Resultado.EXITO,
    request=None,
    usuario=None,
    entidad_afectada="",
    entidad_id="",
    detalle=None,
    codigo_http=None,
):
    """Crea un registro de auditoría.

    Los services lo llaman para eventos de negocio (otorgar una plaza, aprobar
    un plan, consultar datos personales fuera del ámbito...). Las peticiones
    que modifican datos se registran además solas en el middleware.
    Un fallo al auditar nunca interrumpe la operación del usuario.
    """
    if usuario is None and request is not None:
        usuario = getattr(request, "user", None)
    if usuario is not None and not usuario.is_authenticated:
        usuario = None

    try:
        return LogAuditoria.objects.create(
            usuario=usuario,
            usuario_nombre=usuario.get_username() if usuario else "",
            accion=accion[:150],
            modulo=modulo[:60],
            entidad_afectada=entidad_afectada,
            entidad_id=str(entidad_id),
            metodo=request.method if request else "",
            ruta=request.path[:255] if request else "",
            ip=obtener_ip(request) if request else None,
            resultado=resultado,
            codigo_http=codigo_http,
            detalle=detalle or {},
        )
    except Exception:
        logger.exception("No se pudo guardar el registro de auditoría: %s", accion)
        return None
