from .models import LogAuditoria
from .services import registrar

METODOS_AUDITADOS = {"POST", "PUT", "PATCH", "DELETE"}
PREFIJO_API = "/api/v1/"


def _modulo(request):
    """Primer segmento de la ruta tras /api/v1/ (o tras /api/v1/admin/)."""
    partes = [p for p in request.path[len(PREFIJO_API):].split("/") if p]
    if partes and partes[0] == "admin":
        partes = partes[1:]
    return partes[0] if partes else "api"


class AuditoriaMiddleware:
    """Registra toda petición a la API que modifica datos, con su resultado.

    Las lecturas no se registran aquí (serían miles por minuto con el
    polling de notificaciones); las lecturas sensibles las registra cada
    service con `services.registrar`.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.method in METODOS_AUDITADOS and request.path.startswith(PREFIJO_API):
            match = getattr(request, "resolver_match", None)
            registrar(
                request=request,
                accion=f"{request.method} {match.route if match else request.path}"[:150],
                modulo=_modulo(request),
                entidad_id=(match.kwargs.get("pk", "") if match else ""),
                resultado=(
                    LogAuditoria.Resultado.EXITO
                    if response.status_code < 400
                    else LogAuditoria.Resultado.ERROR
                ),
                codigo_http=response.status_code,
            )
        return response
