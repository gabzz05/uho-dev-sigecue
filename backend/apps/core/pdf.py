"""Exportación a PDF con membrete institucional (RE-009) usando WeasyPrint.

WeasyPrint necesita las librerías nativas Pango/GTK (ver docs/DESPLIEGUE.md).
Se importa al usarse: si faltan, el resto del sistema funciona y solo la
exportación a PDF responde con un error claro.

Uso:
    return respuesta_pdf("plan_plazas/plan.html", {"plan": plan}, "plan.pdf", titulo="Plan de plazas 2026-2027")

La plantilla extiende `pdf/base.html` y rellena el bloque `contenido`.
"""

from pathlib import Path

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

from .exceptions import ErrorDeNegocio


def pdf_disponible():
    """True si WeasyPrint y sus librerías nativas están instalados."""
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError):
        return False
    return True


def _membrete():
    from apps.configuracion.models import IdentidadVisual

    identidad = IdentidadVisual.actual()
    escudo = Path(identidad.escudo.path).as_uri() if identidad.escudo else None
    return {"institucion": identidad.nombre_institucion, "escudo": escudo, "color": identidad.color_primario}


def generar_pdf(plantilla, contexto, titulo):
    try:
        from weasyprint import HTML
    except (ImportError, OSError):
        raise ErrorDeNegocio(
            "La exportación a PDF no está disponible en este servidor: faltan las librerías de WeasyPrint (Pango/GTK)."
        )
    html = render_to_string(plantilla, {**contexto, "membrete": _membrete(), "titulo": titulo, "generado": timezone.localtime()})
    return HTML(string=html).write_pdf()


def respuesta_pdf(plantilla, contexto, nombre_archivo, titulo):
    respuesta = HttpResponse(generar_pdf(plantilla, contexto, titulo), content_type="application/pdf")
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
    return respuesta
