from django.db import transaction
from django.utils import timezone

from apps.aspirantes import services as aspirantes
from apps.configuracion.services import parametros
from apps.convocatorias.services import convocatoria_abierta, ofertas_de
from apps.core.exceptions import ErrorDeNegocio
from apps.notificaciones.services import notificar

from . import historial
from .models import EventoHistorial, Solicitud, SolicitudCarrera

E = Solicitud.Estado


def solicitud_actual(usuario):
    """La solicitud de la convocatoria abierta o, si no hay, la más reciente del aspirante."""
    convocatoria = convocatoria_abierta()
    solicitudes = Solicitud.objects.filter(aspirante=usuario).select_related("convocatoria")
    if convocatoria is not None:
        return solicitudes.filter(convocatoria=convocatoria).first()
    return solicitudes.first()


def tiene_carreras(usuario):
    solicitud = solicitud_actual(usuario)
    return solicitud is not None and solicitud.carreras.exists()


def ofertas_disponibles(convocatoria):
    """Carreras que se pueden elegir en la convocatoria (con plazas en el plan publicado)."""
    return ofertas_de(convocatoria).select_related("carrera", "facultad__municipio", "cum_fum__municipio").order_by(
        "carrera__nombre", "facultad__nombre", "cum_fum__nombre"
    )


def _convocatoria_que_acepta():
    convocatoria = convocatoria_abierta()
    if convocatoria is None:
        raise ErrorDeNegocio("No hay una convocatoria de solicitud abierta.")
    return convocatoria


def _bloquear(solicitud):
    solicitud = Solicitud.objects.select_for_update(of=("self",)).select_related("convocatoria").get(pk=solicitud.pk)
    if not solicitud.editable:
        raise ErrorDeNegocio("La solicitud ya no se puede modificar: la convocatoria está cerrada.")
    return solicitud


@transaction.atomic
def obtener_o_crear(usuario):
    """Crea el borrador del aspirante en la convocatoria abierta (o devuelve el que ya tiene)."""
    convocatoria = _convocatoria_que_acepta()
    if Solicitud.objects.filter(aspirante=usuario, estado=Solicitud.Estado.OTORGADA).exists():
        raise ErrorDeNegocio("Ya tienes una plaza otorgada: no puedes presentar otra solicitud.")
    if aspirantes.perfil_bloqueado(usuario):
        raise ErrorDeNegocio(aspirantes.MENSAJE_BLOQUEADO)
    solicitud, _ = Solicitud.objects.get_or_create(aspirante=usuario, convocatoria=convocatoria)
    return solicitud


def validar_seleccion(convocatoria, ofertas):
    """Reglas de RF-047 a RF-049 sobre la lista ordenada de ofertas elegidas."""
    maximo = parametros().max_carreras_aspirante
    if len(ofertas) > maximo:
        raise ErrorDeNegocio(f"Puedes seleccionar como máximo {maximo} carreras.")
    if len({o.pk for o in ofertas}) != len(ofertas):
        raise ErrorDeNegocio("Elegiste la misma carrera en la misma entidad más de una vez.")

    disponibles = set(ofertas_de(convocatoria).filter(pk__in=[o.pk for o in ofertas]).values_list("pk", flat=True))
    if fuera := [o for o in ofertas if o.pk not in disponibles]:
        raise ErrorDeNegocio(f"{fuera[0]} no está disponible en esta convocatoria.")

    # RF-049: por tipo de entidad. Una carrera puede ir en una Facultad y en un
    # CUM/FUM, pero no en dos CUM/FUM (ni en dos Facultades).
    vistas = set()
    for oferta in ofertas:
        clave = (oferta.carrera_id, "facultad" if oferta.facultad_id else "cum_fum")
        if clave in vistas:
            tipo = "dos Facultades" if oferta.facultad_id else "dos CUM/FUM"
            raise ErrorDeNegocio(f"No puedes elegir {oferta.carrera.nombre} en {tipo} distintos.")
        vistas.add(clave)


@transaction.atomic
def guardar_carreras(solicitud, ofertas):
    """Reemplaza la selección por `ofertas`, en orden de prioridad (RF-047, RF-050)."""
    solicitud = _bloquear(solicitud)
    perfil = aspirantes.perfil_de(solicitud.aspirante)
    if not aspirantes.listo_para_carreras(perfil):
        raise ErrorDeNegocio("Completa tu perfil antes de seleccionar carreras.")
    if not ofertas and solicitud.estado != E.BORRADOR:
        raise ErrorDeNegocio("Una solicitud confirmada debe tener al menos una carrera.")
    validar_seleccion(solicitud.convocatoria, ofertas)

    antes = historial.instantanea_seleccion(solicitud)
    solicitud.carreras.all().delete()
    SolicitudCarrera.objects.bulk_create(
        [SolicitudCarrera(solicitud=solicitud, oferta=oferta, prioridad=i) for i, oferta in enumerate(ofertas, start=1)]
    )
    solicitud.modificada_at = timezone.now()
    solicitud.save(update_fields=["modificada_at"])
    despues = historial.instantanea_seleccion(solicitud)
    if antes != despues:
        historial.registrar(
            solicitud.aspirante, EventoHistorial.Tipo.SELECCION, "Cambió la selección de carreras",
            usuario=solicitud.aspirante, solicitud=solicitud, antes=antes, despues=despues,
        )
    aspirantes.actualizar_perfil_completo(perfil)
    return solicitud


@transaction.atomic
def confirmar(solicitud):
    """Presenta oficialmente la solicitud: pasa a Pendiente y avisa al aspirante (paso 16 de 7.2)."""
    solicitud = _bloquear(solicitud)
    if solicitud.estado != E.BORRADOR:
        raise ErrorDeNegocio("La solicitud ya está confirmada.")
    perfil = aspirantes.perfil_de(solicitud.aspirante)
    requisitos = aspirantes.requisitos_perfil(perfil)
    if faltan := [aspirantes.REQUISITOS[clave] for clave, cumple in requisitos.items() if not cumple]:
        raise ErrorDeNegocio("Para confirmar la solicitud falta: " + ", ".join(faltan).lower() + ".")

    solicitud.estado = E.PENDIENTE
    solicitud.confirmada_at = timezone.now()
    solicitud.save(update_fields=["estado", "confirmada_at"])
    aspirantes.actualizar_perfil_completo(perfil)
    historial.registrar(
        solicitud.aspirante, EventoHistorial.Tipo.CONFIRMACION, "Confirmó la solicitud",
        usuario=solicitud.aspirante, solicitud=solicitud, despues=historial.instantanea_seleccion(solicitud),
    )

    convocatoria = solicitud.convocatoria
    carreras = solicitud.carreras.select_related("oferta__carrera", "oferta__facultad", "oferta__cum_fum")
    notificar(
        [solicitud.aspirante],
        "solicitud_confirmada",
        {
            "anio": convocatoria.anio_academico,
            "convocatoria": f"{convocatoria.numero}.ª",
            "fecha_cierre": convocatoria.fecha_cierre.strftime("%d/%m/%Y"),
            "carreras": "\n".join(f"{c.prioridad}. {c.oferta.carrera.nombre} — {c.oferta.entidad}" for c in carreras),
        },
    )
    return solicitud
