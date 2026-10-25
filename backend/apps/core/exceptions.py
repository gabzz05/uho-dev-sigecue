"""Formato uniforme de errores de la API (RG-003).

Toda respuesta de error tiene la forma:

    {"error": {"codigo": "...", "mensaje": "...", "detalles": {...}}}

`mensaje` es un texto en español pensado para mostrarse al usuario;
`detalles` (opcional) lleva los errores por campo de las validaciones.
"""

import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)

MENSAJES = {
    "not_authenticated": "Debes iniciar sesión para realizar esta acción.",
    "authentication_failed": "No se pudo verificar tu identidad. Inicia sesión de nuevo.",
    "permission_denied": "No tienes permiso para realizar esta acción.",
    "not_found": "El recurso solicitado no existe.",
    "method_not_allowed": "Esta operación no está permitida.",
    "throttled": "Demasiadas solicitudes. Espera un momento e inténtalo de nuevo.",
    "invalid": "Revisa los datos marcados e inténtalo de nuevo.",
    "parse_error": "La solicitud no tiene un formato válido.",
    "unsupported_media_type": "El tipo de contenido enviado no es válido.",
    "error_interno": "Ocurrió un error inesperado. Inténtalo más tarde.",
}


class ErrorDeNegocio(exceptions.APIException):
    """Regla de negocio incumplida. Se lanza desde los services con un mensaje claro."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "regla_de_negocio"
    default_detail = "La operación no cumple las reglas del proceso."


def _error(codigo, mensaje, detalles=None):
    cuerpo = {"codigo": codigo, "mensaje": mensaje}
    if detalles:
        cuerpo["detalles"] = detalles
    return {"error": cuerpo}


def exception_handler(exc, context):
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)

    if response is None:
        logger.exception("Error no controlado en %s", context.get("view"))
        return Response(
            _error("error_interno", MENSAJES["error_interno"]),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, exceptions.ValidationError):
        codigo = "invalid"
        detalles = exc.detail if isinstance(exc.detail, dict) else {"no_field_errors": exc.detail}
        response.data = _error(codigo, MENSAJES[codigo], detalles)
        return response

    codigo = exc.get_codes() if isinstance(exc.get_codes(), str) else exc.default_code
    if isinstance(exc, ErrorDeNegocio):
        mensaje = str(exc.detail)
    else:
        mensaje = MENSAJES.get(codigo, str(exc.detail))
    response.data = _error(codigo, mensaje)
    return response
