"""Revisión de solicitudes por las entidades (RF-052 a RF-055).

- Una entidad ve las solicitudes confirmadas con alguna opción suya, y de cada
  una solo sus opciones. Los roles globales lo ven todo.
- Revisan (validar el índice y observar) quienes tienen `solicitudes.editar`
  y la solicitud tiene una opción en su entidad.
- La primera acción de revisión pasa la solicitud de Pendiente a En revisión.
- Una observación no resuelta saca la solicitud completa del ranking. Si
  `afecta_elegibilidad`, además anula el índice validado y marca la revisión
  documental como pendiente.
"""

from django.db import transaction
from django.utils import timezone

from apps.aspirantes import services as aspirantes
from apps.aspirantes.models import PerfilAspirante
from apps.core.exceptions import ErrorDeNegocio
from apps.notificaciones.services import notificar
from apps.roles.catalogo import EDITAR

from . import historial
from .models import EventoHistorial, Observacion, Solicitud, SolicitudCarrera

E = Solicitud.Estado
EO = Observacion.Estado
T = EventoHistorial.Tipo

# Estados en los que la solicitud se puede revisar.
REVISABLES = (E.PENDIENTE, E.EN_REVISION, E.OBSERVADA)


# --- Ámbito -----------------------------------------------------------------


def opciones_de_su_entidad(usuario, qs=None):
    """Opciones (SolicitudCarrera) que el usuario puede ver: todas si es global, las de su entidad si es local."""
    qs = SolicitudCarrera.objects.all() if qs is None else qs
    if usuario.es_global:
        return qs
    if usuario.facultad_id:
        return qs.filter(oferta__facultad_id=usuario.facultad_id)
    if usuario.cum_fum_id:
        return qs.filter(oferta__cum_fum_id=usuario.cum_fum_id)
    return qs.none()


def solicitudes_visibles(usuario):
    """Solicitudes confirmadas (los borradores no se presentaron) dentro del ámbito del usuario."""
    qs = Solicitud.objects.exclude(estado=E.BORRADOR)
    if usuario.es_global:
        return qs
    return qs.filter(pk__in=opciones_de_su_entidad(usuario).values("solicitud"))


def puede_revisar(usuario, solicitud):
    if not usuario.tiene_permiso("solicitudes", EDITAR):
        return False
    return usuario.es_global or opciones_de_su_entidad(usuario, solicitud.carreras.all()).exists()


def puede_gestionar(usuario, observacion):
    """Cada entidad edita, resuelve y reabre solo sus observaciones; los roles globales, cualquiera."""
    if not puede_revisar(usuario, observacion.solicitud):
        return False
    if usuario.es_global:
        return True
    return (observacion.facultad_id, observacion.cum_fum_id) == (usuario.facultad_id, usuario.cum_fum_id)


def revision_cerrada(solicitud):
    """Generado el otorgamiento de la convocatoria, la revisión queda cerrada: el resultado es un snapshot."""
    from apps.otorgamiento.models import Otorgamiento

    return Otorgamiento.objects.filter(convocatoria_id=solicitud.convocatoria_id).exists()


MENSAJE_CERRADA = "Ya se generó el otorgamiento de esta convocatoria: la revisión está cerrada."


def admite_revision(solicitud):
    return solicitud.estado in REVISABLES and not revision_cerrada(solicitud)


def _exigir_revisable(usuario, solicitud):
    if not puede_revisar(usuario, solicitud):
        raise ErrorDeNegocio("No puedes revisar esta solicitud.")
    if solicitud.estado not in REVISABLES:
        raise ErrorDeNegocio("Esta solicitud ya no admite revisión.")
    if revision_cerrada(solicitud):
        raise ErrorDeNegocio(MENSAJE_CERRADA)


# --- Elegibilidad -----------------------------------------------------------


def motivos_no_elegible(solicitud):
    """Por qué la solicitud no entraría hoy en el ranking del otorgamiento (vacío = elegible)."""
    motivos = []
    if solicitud.estado not in (E.PENDIENTE, E.EN_REVISION):
        motivos.append(f"Estado: {solicitud.get_estado_display()}")
    if solicitud.observaciones.filter(estado__in=Observacion.NO_RESUELTAS).exists():
        motivos.append("Tiene observaciones sin resolver")
    perfil = aspirantes.perfil_de(solicitud.aspirante)
    if perfil.indice_validado is None:
        motivos.append("Índice académico sin validar")
    if not aspirantes.calcular_perfil_completo(perfil):
        motivos.append("Perfil incompleto")
    return motivos


# --- Transiciones -----------------------------------------------------------


def _bloquear(solicitud):
    return Solicitud.objects.select_for_update().select_related("aspirante", "convocatoria").get(pk=solicitud.pk)


def _iniciar_revision(solicitud):
    if solicitud.estado == E.PENDIENTE:
        solicitud.estado = E.EN_REVISION
        solicitud.save(update_fields=["estado"])


def _anular_indice(solicitud):
    PerfilAspirante.objects.filter(usuario=solicitud.aspirante).update(
        indice_validado=None, indice_validado_por=None, indice_validado_at=None
    )
    solicitud.revision_documental_pendiente = True
    solicitud.save(update_fields=["revision_documental_pendiente"])


def _entidad_autora(usuario):
    if usuario.es_global:
        return {"facultad": None, "cum_fum": None}
    return {"facultad": usuario.facultad, "cum_fum": usuario.cum_fum}


def _avisar_observacion(observacion, plantilla_texto):
    solicitud = observacion.solicitud
    notificar(
        [solicitud.aspirante],
        "solicitud_observada",
        {
            "anio": solicitud.convocatoria.anio_academico,
            "elemento": observacion.elemento,
            "observacion": plantilla_texto,
        },
    )


@transaction.atomic
def validar_indice(usuario, solicitud, valor):
    """Fija el índice validado contra la certificación. Una sola validación; después solo un rol global lo cambia."""
    solicitud = _bloquear(solicitud)
    _exigir_revisable(usuario, solicitud)
    perfil = PerfilAspirante.objects.select_for_update().select_related("indice_validado_por").get(usuario=solicitud.aspirante)
    if perfil.indice_validado is not None and not usuario.es_global:
        por = perfil.indice_validado_por.nombre_completo if perfil.indice_validado_por else "otra entidad"
        raise ErrorDeNegocio(f"El índice ya lo validó {por}. Solo la Comisión de Ingreso puede cambiarlo.")
    observadas = solicitud.observaciones.filter(objetivo=Observacion.Objetivo.INDICE, estado__in=Observacion.PENDIENTES_DE_CORREGIR)
    if observadas.exists():
        raise ErrorDeNegocio("El índice tiene una observación pendiente de corregir por el aspirante.")

    anterior = perfil.indice_validado
    perfil.indice_validado = valor
    perfil.indice_validado_por = usuario
    perfil.indice_validado_at = timezone.now()
    perfil.save(update_fields=["indice_validado", "indice_validado_por", "indice_validado_at"])
    # La validación cierra la revisión documental pendiente en todas sus solicitudes.
    Solicitud.objects.filter(aspirante=solicitud.aspirante, revision_documental_pendiente=True).update(revision_documental_pendiente=False)
    solicitud.refresh_from_db(fields=["revision_documental_pendiente"])
    _iniciar_revision(solicitud)
    historial.registrar(
        solicitud.aspirante, T.INDICE_VALIDADO, f"Validó el índice académico: {valor}",
        usuario=usuario, solicitud=solicitud,
        antes=None if anterior is None else str(anterior), despues=str(valor),
    )
    return solicitud


@transaction.atomic
def crear_observacion(usuario, solicitud, *, objetivo, texto, tipo_documento=None, afecta_elegibilidad=None):
    solicitud = _bloquear(solicitud)
    _exigir_revisable(usuario, solicitud)
    O = Observacion.Objetivo
    if objetivo == O.DOCUMENTO:
        if tipo_documento is None:
            raise ErrorDeNegocio("Indica qué documento observas.")
        if not tipo_documento.activo:
            raise ErrorDeNegocio("Ese documento ya no se pide: el aspirante no podría corregirlo.")
    else:
        tipo_documento = None

    repetida = solicitud.observaciones.filter(objetivo=objetivo, tipo_documento=tipo_documento, estado__in=Observacion.NO_RESUELTAS)
    if repetida.exists():
        raise ErrorDeNegocio("Ya hay una observación sin resolver sobre ese elemento.")

    if afecta_elegibilidad is None:
        afecta_elegibilidad = objetivo == O.INDICE or bool(tipo_documento and tipo_documento.afecta_elegibilidad)

    observacion = Observacion.objects.create(
        solicitud=solicitud, autor=usuario, objetivo=objetivo, tipo_documento=tipo_documento,
        texto=texto, afecta_elegibilidad=afecta_elegibilidad, **_entidad_autora(usuario),
    )
    if afecta_elegibilidad:
        _anular_indice(solicitud)
    solicitud.estado = E.OBSERVADA
    solicitud.save(update_fields=["estado"])
    historial.registrar(
        solicitud.aspirante, T.OBSERVACION_CREADA, f"Observó: {observacion.elemento}",
        usuario=usuario, solicitud=solicitud, despues={"texto": texto, "afecta_elegibilidad": afecta_elegibilidad},
    )
    _avisar_observacion(observacion, texto)
    return observacion


def _bloquear_observacion(observacion):
    return Observacion.objects.select_for_update().select_related("solicitud__aspirante", "solicitud__convocatoria", "tipo_documento").get(
        pk=observacion.pk
    )


def _exigir_gestionable(usuario, observacion):
    if not puede_gestionar(usuario, observacion):
        raise ErrorDeNegocio("Solo la entidad que hizo la observación (o la Comisión de Ingreso) puede gestionarla.")
    if not admite_revision(observacion.solicitud):
        raise ErrorDeNegocio(MENSAJE_CERRADA if revision_cerrada(observacion.solicitud) else "Esta solicitud ya no admite revisión.")


@transaction.atomic
def editar_observacion(usuario, observacion, *, texto=None, afecta_elegibilidad=None):
    observacion = _bloquear_observacion(observacion)
    _exigir_gestionable(usuario, observacion)
    if observacion.estado == EO.RESUELTA:
        raise ErrorDeNegocio("Una observación resuelta no se edita. Si hace falta, crea otra.")
    antes = {"texto": observacion.texto, "afecta_elegibilidad": observacion.afecta_elegibilidad}
    if texto is not None:
        observacion.texto = texto
    if afecta_elegibilidad is not None:
        if afecta_elegibilidad and not observacion.afecta_elegibilidad:
            _anular_indice(observacion.solicitud)
        observacion.afecta_elegibilidad = afecta_elegibilidad
    observacion.save()
    historial.registrar(
        observacion.solicitud.aspirante, T.OBSERVACION_EDITADA, f"Editó la observación: {observacion.elemento}",
        usuario=usuario, solicitud=observacion.solicitud,
        antes=antes, despues={"texto": observacion.texto, "afecta_elegibilidad": observacion.afecta_elegibilidad},
    )
    return observacion


@transaction.atomic
def resolver_observacion(usuario, observacion):
    observacion = _bloquear_observacion(observacion)
    _exigir_gestionable(usuario, observacion)
    if observacion.estado == EO.RESUELTA:
        raise ErrorDeNegocio("La observación ya está resuelta.")
    observacion.estado = EO.RESUELTA
    observacion.resuelta_at = timezone.now()
    observacion.resuelta_por = usuario
    observacion.save()

    solicitud = _bloquear(observacion.solicitud)
    quedan = solicitud.observaciones.filter(estado__in=Observacion.PENDIENTES_DE_CORREGIR).exists()
    solicitud.estado = E.OBSERVADA if quedan else E.EN_REVISION
    solicitud.save(update_fields=["estado"])
    historial.registrar(
        solicitud.aspirante, T.OBSERVACION_RESUELTA, f"Resolvió la observación: {observacion.elemento}",
        usuario=usuario, solicitud=solicitud,
    )
    return observacion


@transaction.atomic
def reabrir_observacion(usuario, observacion, motivo):
    """La entidad rechaza la corrección: la observación vuelve a pedir corrección al aspirante."""
    observacion = _bloquear_observacion(observacion)
    _exigir_gestionable(usuario, observacion)
    if observacion.estado != EO.CORREGIDA:
        raise ErrorDeNegocio("Solo se reabre una observación que el aspirante ya corrigió.")
    observacion.estado = EO.REABIERTA
    observacion.save()

    solicitud = _bloquear(observacion.solicitud)
    if observacion.afecta_elegibilidad:
        _anular_indice(solicitud)
    solicitud.estado = E.OBSERVADA
    solicitud.save(update_fields=["estado"])
    historial.registrar(
        solicitud.aspirante, T.OBSERVACION_REABIERTA, f"Reabrió la observación: {observacion.elemento}",
        usuario=usuario, solicitud=solicitud, despues={"motivo": motivo},
    )
    _avisar_observacion(observacion, motivo)
    return observacion


@transaction.atomic
def enviar_correccion(solicitud):
    """El aspirante da por corregido lo observado: las observaciones pasan a Corregida y la solicitud a Pendiente."""
    solicitud = _bloquear(solicitud)
    if solicitud.estado != E.OBSERVADA:
        raise ErrorDeNegocio("Tu solicitud no tiene observaciones pendientes de corregir.")
    if revision_cerrada(solicitud):
        raise ErrorDeNegocio("Ya se generó el otorgamiento de esta convocatoria: no se admiten más correcciones en ella.")
    pendientes = list(
        solicitud.observaciones.filter(estado__in=Observacion.PENDIENTES_DE_CORREGIR).select_related("autor", "tipo_documento")
    )
    ahora = timezone.now()
    for observacion in pendientes:
        observacion.estado = EO.CORREGIDA
        observacion.corregida_at = ahora
        observacion.save(update_fields=["estado", "corregida_at", "updated_at"])
    solicitud.estado = E.PENDIENTE
    solicitud.save(update_fields=["estado"])
    historial.registrar(
        solicitud.aspirante, T.OBSERVACION_CORREGIDA,
        "Corrigió: " + ", ".join(o.elemento for o in pendientes),
        usuario=solicitud.aspirante, solicitud=solicitud,
    )
    autores = {o.autor for o in pendientes if o.autor is not None}
    if autores:
        notificar(
            autores, "observacion_corregida",
            lambda autor: {
                "aspirante": solicitud.aspirante.nombre_completo,
                "elementos": ", ".join(o.elemento for o in pendientes if o.autor == autor),
            },
            por_correo=False,
        )
    return solicitud


def objetivos_a_corregir(usuario):
    """Elementos del perfil que el aspirante puede corregir aunque esté congelado (observaciones por corregir)."""
    pendientes = Observacion.objects.filter(solicitud__aspirante=usuario, estado__in=Observacion.PENDIENTES_DE_CORREGIR)
    return {
        (o.objetivo, o.tipo_documento_id) if o.objetivo == Observacion.Objetivo.DOCUMENTO else (o.objetivo, None)
        for o in pendientes
    }

