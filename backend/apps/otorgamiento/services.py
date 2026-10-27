from collections import Counter

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.aspirantes.models import PerfilAspirante
from apps.convocatorias.models import ConvocatoriaSolicitud
from apps.core.exceptions import ErrorDeNegocio
from apps.notificaciones.services import notificar
from apps.oferta.models import OfertaCarrera
from apps.roles.catalogo import APROBAR, GENERAR, PUBLICAR
from apps.solicitudes import revision
from apps.solicitudes.models import Solicitud, SolicitudCarrera
from apps.users.models import Usuario

from .algoritmo import Candidato, PlazasInsuficientes, repartir
from .models import AjusteOtorgamiento, Otorgamiento, ResultadoOtorgamiento

E = Otorgamiento.Estado
ES = Solicitud.Estado
MODULO = "otorgamiento"


# --- Plazas ------------------------------------------------------------------


def otorgadas_publicadas(anio_academico, antes_de=None):
    """Plazas ya otorgadas en otorgamientos publicados del año: `{oferta_id: cantidad}`."""
    resultados = ResultadoOtorgamiento.objects.filter(
        otorgamiento__estado=E.PUBLICADO, otorgamiento__convocatoria__anio_academico=anio_academico, otorgada__isnull=False
    )
    if antes_de is not None:
        resultados = resultados.filter(otorgamiento__convocatoria__numero__lt=antes_de)
    return dict(resultados.values_list("otorgada__oferta_id").annotate(n=Count("pk")))


def plazas_restantes(convocatoria):
    """RF-062: plazas del plan menos las otorgadas en las convocatorias anteriores del mismo año."""
    from apps.convocatorias.services import ofertas_de

    previas = otorgadas_publicadas(convocatoria.anio_academico, antes_de=convocatoria.numero)
    return {o.pk: o.plazas_plan - previas.get(o.pk, 0) for o in ofertas_de(convocatoria, con_restantes=False)}


# --- Generación --------------------------------------------------------------


def _convocatoria_lista(convocatoria):
    if convocatoria.estado != ConvocatoriaSolicitud.Estado.CERRADA:
        raise ErrorDeNegocio("El otorgamiento se genera cuando la convocatoria está cerrada.")
    if Otorgamiento.objects.filter(convocatoria=convocatoria).exists():
        raise ErrorDeNegocio("El otorgamiento de esta convocatoria ya se generó: no se puede volver a ejecutar.")


def _solicitudes(convocatoria):
    return (
        Solicitud.objects.filter(convocatoria=convocatoria)
        .exclude(estado=ES.BORRADOR)
        .select_related("aspirante", "convocatoria")
        .prefetch_related("carreras__oferta__carrera", "carreras__oferta__facultad", "carreras__oferta__cum_fum")
    )


def _evaluar(convocatoria):
    """Elegibilidad de cada solicitud confirmada: `[(solicitud, motivos)]`."""
    return [(s, revision.motivos_no_elegible(s)) for s in _solicitudes(convocatoria)]


def _resumen(evaluadas, capacidad):
    motivos = Counter(m for _, lista in evaluadas for m in lista)
    return {
        "solicitudes": len(evaluadas),
        "elegibles": sum(1 for _, lista in evaluadas if not lista),
        "no_elegibles": sum(1 for _, lista in evaluadas if lista),
        "motivos": [{"motivo": m, "cantidad": n} for m, n in motivos.most_common()],
        "plazas": sum(max(p, 0) for p in capacidad.values()),
    }


def previsualizar(convocatoria):
    """Lo que se mostrará antes de confirmar: elegibles, no elegibles y por qué."""
    _convocatoria_lista(convocatoria)
    return _resumen(_evaluar(convocatoria), plazas_restantes(convocatoria))


def _opciones(solicitud):
    return [
        {
            "opcion": c.pk, "oferta": c.oferta_id, "prioridad": c.prioridad,
            "carrera": c.oferta.carrera.nombre, "entidad": str(c.oferta.entidad),
        }
        for c in sorted(solicitud.carreras.all(), key=lambda c: c.prioridad)
    ]


@transaction.atomic
def generar(usuario, convocatoria):
    """Genera el ranking y el reparto automático (RF-057, RF-058). Una sola vez por convocatoria."""
    if not usuario.tiene_permiso(MODULO, GENERAR):
        raise ErrorDeNegocio("Solo la Secretaría General genera el otorgamiento.")
    convocatoria = ConvocatoriaSolicitud.objects.select_for_update().get(pk=convocatoria.pk)
    _convocatoria_lista(convocatoria)

    capacidad = plazas_restantes(convocatoria)
    evaluadas = _evaluar(convocatoria)
    indices = dict(PerfilAspirante.objects.filter(usuario__in=[s.aspirante_id for s, _ in evaluadas]).values_list("usuario", "indice_validado"))
    otorgamiento = Otorgamiento.objects.create(
        convocatoria=convocatoria, generado_por=usuario,
        capacidad={str(k): v for k, v in capacidad.items()}, resumen=_resumen(evaluadas, capacidad),
    )

    elegibles = sorted(
        (s for s, motivos in evaluadas if not motivos),
        key=lambda s: (-indices[s.aspirante_id], s.confirmada_at, s.pk),
    )
    posicion = {s.pk: i for i, s in enumerate(elegibles, start=1)}
    ResultadoOtorgamiento.objects.bulk_create(
        [
            ResultadoOtorgamiento(
                otorgamiento=otorgamiento, solicitud=s, aspirante=s.aspirante, aspirante_nombre=s.aspirante.nombre_completo,
                indice_utilizado=indices.get(s.aspirante_id), confirmada_at=s.confirmada_at,
                posicion_ranking=posicion.get(s.pk), motivo_exclusion="; ".join(motivos)[:255], opciones=_opciones(s),
            )
            for s, motivos in evaluadas
        ]
    )
    _recalcular(otorgamiento)
    return otorgamiento


# --- Reparto y ajustes --------------------------------------------------------


def _texto(resultado):
    return f"{resultado.carrera} — {resultado.entidad}" if resultado.otorgada_id else None


def _recalcular(otorgamiento):
    """Aplica los ajustes vigentes y reparte las vacantes por ranking. Devuelve qué cambió."""
    resultados = list(otorgamiento.resultados.filter(posicion_ranking__isnull=False).order_by("posicion_ranking"))
    fijados, prohibidos = {}, set()
    for ajuste in otorgamiento.ajustes.filter(activo=True).order_by("created_at", "id"):
        clave = (ajuste.resultado_id, ajuste.opcion_id)
        if ajuste.tipo == AjusteOtorgamiento.Tipo.OTORGAR:
            fijados[ajuste.resultado_id] = ajuste.opcion_id
            prohibidos.discard(clave)
        else:
            prohibidos.add(clave)
            if fijados.get(ajuste.resultado_id) == ajuste.opcion_id:
                del fijados[ajuste.resultado_id]

    candidatos = [Candidato(r.pk, [(o["opcion"], o["oferta"]) for o in r.opciones]) for r in resultados]
    capacidad = {int(k): v for k, v in otorgamiento.capacidad.items()}
    asignacion, _ = repartir(candidatos, capacidad, fijados, prohibidos)

    cambios = []
    for resultado in resultados:
        nueva = asignacion[resultado.pk]
        tipo = ResultadoOtorgamiento.Tipo.MANUAL if resultado.pk in fijados else ResultadoOtorgamiento.Tipo.AUTOMATICA
        if nueva == resultado.otorgada_id and (nueva is None or tipo == resultado.tipo):
            continue
        antes = _texto(resultado)
        opcion = next((o for o in resultado.opciones if o["opcion"] == nueva), None)
        resultado.otorgada_id = nueva
        resultado.carrera = opcion["carrera"] if opcion else ""
        resultado.entidad = opcion["entidad"] if opcion else ""
        resultado.prioridad = opcion["prioridad"] if opcion else None
        resultado.tipo = tipo if opcion else ""
        resultado.save(update_fields=["otorgada", "carrera", "entidad", "prioridad", "tipo"])
        if antes != _texto(resultado):
            cambios.append({"resultado": resultado.pk, "aspirante": resultado.aspirante_nombre, "antes": antes, "despues": _texto(resultado)})
    return cambios


def permiso_de_etapa(otorgamiento):
    """Quién edita y aprueba en cada etapa: el Jefe CI en la revisión, el Vicerrector en la aprobación."""
    return {E.REVISION_CI: APROBAR, E.APROBACION: PUBLICAR}.get(otorgamiento.estado)


def puede_editar(usuario, otorgamiento):
    permiso = permiso_de_etapa(otorgamiento)
    return permiso is not None and usuario.tiene_permiso(MODULO, permiso)


def _bloquear(usuario, otorgamiento):
    otorgamiento = Otorgamiento.objects.select_for_update().select_related("convocatoria").get(pk=otorgamiento.pk)
    if otorgamiento.publicado:
        raise ErrorDeNegocio("El otorgamiento está publicado: ya no admite cambios.")
    if not puede_editar(usuario, otorgamiento):
        raise ErrorDeNegocio(
            "En esta etapa el otorgamiento lo revisa el Jefe de la Comisión de Ingreso."
            if otorgamiento.estado == E.REVISION_CI
            else "En esta etapa el otorgamiento lo revisa el Vicerrector de Formación."
        )
    return otorgamiento


def _aplicar(otorgamiento, ajuste):
    try:
        cambios = _recalcular(otorgamiento)
    except PlazasInsuficientes as error:
        oferta = OfertaCarrera.objects.select_related("carrera", "facultad", "cum_fum").get(pk=error.oferta_id)
        raise ErrorDeNegocio(f"No quedan plazas en {oferta.carrera.nombre} — {oferta.entidad}. Quita antes la plaza a otro aspirante.")
    ajuste.cambios = cambios
    ajuste.save(update_fields=["cambios"])
    return ajuste


@transaction.atomic
def ajustar(usuario, otorgamiento, resultado, tipo, opcion, justificacion):
    otorgamiento = _bloquear(usuario, otorgamiento)
    if resultado.otorgamiento_id != otorgamiento.pk:
        raise ErrorDeNegocio("Ese aspirante no pertenece a este otorgamiento.")
    if not resultado.elegible:
        raise ErrorDeNegocio(f"{resultado.aspirante_nombre} no es elegible ({resultado.motivo_exclusion}): no se le puede otorgar plaza.")
    if opcion.solicitud_id != resultado.solicitud_id:
        raise ErrorDeNegocio("Solo se puede otorgar una de las carreras que el aspirante solicitó.")
    if tipo == AjusteOtorgamiento.Tipo.OTORGAR and resultado.otorgada_id == opcion.pk:
        raise ErrorDeNegocio("El aspirante ya tiene esa plaza.")
    if tipo == AjusteOtorgamiento.Tipo.QUITAR and resultado.otorgada_id != opcion.pk:
        raise ErrorDeNegocio("El aspirante no tiene esa plaza.")
    ajuste = AjusteOtorgamiento.objects.create(
        otorgamiento=otorgamiento, resultado=resultado, tipo=tipo, opcion=opcion, justificacion=justificacion, usuario=usuario
    )
    return _aplicar(otorgamiento, ajuste)


@transaction.atomic
def anular_ajuste(usuario, ajuste, justificacion):
    otorgamiento = _bloquear(usuario, ajuste.otorgamiento)
    ajuste = AjusteOtorgamiento.objects.select_for_update().get(pk=ajuste.pk)
    if not ajuste.activo:
        raise ErrorDeNegocio("El ajuste ya estaba anulado.")
    ajuste.activo = False
    ajuste.anulado_por = usuario
    ajuste.anulado_at = timezone.now()
    ajuste.justificacion_anulacion = justificacion
    ajuste.save(update_fields=["activo", "anulado_por", "anulado_at", "justificacion_anulacion"])
    cambios = _recalcular(otorgamiento)
    return ajuste, cambios


# --- Aprobación y publicación ---------------------------------------------------


def _con_permiso(accion):
    return Usuario.objects.filter(is_active=True, rol__activo=True, rol__permisos__modulo=MODULO, rol__permisos__accion=accion).distinct()


@transaction.atomic
def aprobar(usuario, otorgamiento):
    """El Jefe CI aprueba y lo pasa al Vicerrector."""
    otorgamiento = _bloquear(usuario, otorgamiento)
    if otorgamiento.estado != E.REVISION_CI:
        raise ErrorDeNegocio("El otorgamiento ya fue aprobado por el Jefe CI.")
    otorgamiento.estado = E.APROBACION
    otorgamiento.aprobado_por = usuario
    otorgamiento.aprobado_at = timezone.now()
    otorgamiento.save(update_fields=["estado", "aprobado_por", "aprobado_at"])
    convocatoria = otorgamiento.convocatoria
    notificar(
        _con_permiso(PUBLICAR), "otorgamiento_para_aprobacion",
        {"anio": convocatoria.anio_academico, "convocatoria": f"{convocatoria.numero}.ª"},
    )
    return otorgamiento


@transaction.atomic
def publicar(usuario, otorgamiento, segunda_convocatoria):
    """La aprobación del Vicerrector publica: congela el resultado, cambia los estados y avisa (RF-060, RF-061)."""
    otorgamiento = _bloquear(usuario, otorgamiento)
    if otorgamiento.estado != E.APROBACION:
        raise ErrorDeNegocio("Antes de publicar, el Jefe CI debe aprobar el otorgamiento.")
    otorgamiento.estado = E.PUBLICADO
    otorgamiento.publicado_por = usuario
    otorgamiento.publicado_at = timezone.now()
    otorgamiento.segunda_convocatoria = segunda_convocatoria
    otorgamiento.save(update_fields=["estado", "publicado_por", "publicado_at", "segunda_convocatoria"])

    resultados = list(otorgamiento.resultados.select_related("aspirante"))
    otorgadas = [r for r in resultados if r.otorgada_id]
    sin_plaza = [r for r in resultados if not r.otorgada_id]
    solicitudes = [r.solicitud_id for r in resultados]

    SolicitudCarrera.objects.filter(solicitud_id__in=solicitudes).update(estado=SolicitudCarrera.Estado.NO_SELECCIONADA)
    SolicitudCarrera.objects.filter(pk__in=[r.otorgada_id for r in otorgadas]).update(estado=SolicitudCarrera.Estado.OTORGADA)
    Solicitud.objects.filter(pk__in=[r.solicitud_id for r in otorgadas]).update(estado=ES.OTORGADA)
    Solicitud.objects.filter(pk__in=[r.solicitud_id for r in sin_plaza]).update(estado=ES.NO_SELECCIONADO)

    anio = otorgamiento.convocatoria.anio_academico
    por_aspirante = {r.aspirante_id: r for r in otorgadas}
    notificar(
        [r.aspirante for r in otorgadas], "plaza_otorgada",
        lambda u: {"anio": anio, "carrera": por_aspirante[u.pk].carrera, "entidad": por_aspirante[u.pk].entidad},
    )
    notificar(
        [r.aspirante for r in sin_plaza],
        "no_seleccionado_segunda" if segunda_convocatoria else "no_seleccionado_final",
        {"anio": anio},
    )
    return otorgamiento


def resultados_visibles(usuario, otorgamiento):
    """Provisional: solo roles globales. Publicado: las entidades ven lo otorgado en ellas."""
    resultados = otorgamiento.resultados.select_related("otorgada__oferta")
    if usuario.es_global:
        return resultados
    if not otorgamiento.publicado:
        return resultados.none()
    if usuario.facultad_id:
        return resultados.filter(otorgada__oferta__facultad_id=usuario.facultad_id)
    if usuario.cum_fum_id:
        return resultados.filter(otorgada__oferta__cum_fum_id=usuario.cum_fum_id)
    return resultados.none()


def plazas_por_oferta(otorgamiento, usuario):
    """Plazas disponibles y otorgadas por oferta (dentro del ámbito del usuario)."""
    otorgadas = dict(
        otorgamiento.resultados.filter(otorgada__isnull=False).values_list("otorgada__oferta_id").annotate(n=Count("pk"))
    )
    ofertas = OfertaCarrera.objects.filter(pk__in=[int(k) for k in otorgamiento.capacidad]).select_related("carrera", "facultad", "cum_fum")
    if not usuario.es_global:
        ofertas = ofertas.filter(facultad_id=usuario.facultad_id) if usuario.facultad_id else ofertas.filter(cum_fum_id=usuario.cum_fum_id)
    filas = [
        {
            "oferta": o.pk, "carrera": o.carrera.nombre, "entidad": str(o.entidad),
            "plazas": otorgamiento.capacidad[str(o.pk)], "otorgadas": otorgadas.get(o.pk, 0),
        }
        for o in ofertas
    ]
    return sorted(filas, key=lambda f: (f["carrera"], f["entidad"]))
