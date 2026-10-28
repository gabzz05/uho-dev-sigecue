"""Listado filtrado, estadísticas y exportación de solicitudes (RF-052, RF-053, RF-056)."""

from django.db.models import Count, F, Q
from django.db.models.functions import Coalesce, TruncDate

from apps.convocatorias.models import ConvocatoriaSolicitud
from apps.convocatorias.services import ofertas_de
from apps.core import crypto
from apps.core.exceptions import ErrorDeNegocio

from . import revision
from .models import Observacion, Solicitud, SolicitudCarrera

E = Solicitud.Estado
INDICE = Coalesce("aspirante__perfil_aspirante__indice_validado", "aspirante__perfil_aspirante__indice_declarado")


def _opciones_filtradas(usuario, params):
    """Opciones dentro del ámbito que cumplen los filtros de carrera y entidad (la misma fila debe cumplir ambos)."""
    opciones = revision.opciones_de_su_entidad(usuario)
    if carrera := params.get("carrera"):
        opciones = opciones.filter(oferta__carrera_id=carrera)
    if facultad := params.get("facultad"):
        opciones = opciones.filter(oferta__facultad_id=facultad)
    if cum_fum := params.get("cum_fum"):
        opciones = opciones.filter(oferta__cum_fum_id=cum_fum)
    return opciones


def listado(usuario, params):
    """Solicitudes confirmadas del ámbito del usuario con los filtros de RF-052."""
    qs = (
        revision.solicitudes_visibles(usuario)
        .filter(pk__in=_opciones_filtradas(usuario, params).values("solicitud"))
        .select_related("aspirante__perfil_aspirante", "convocatoria")
        .prefetch_related("carreras__oferta__carrera", "carreras__oferta__facultad__municipio", "carreras__oferta__cum_fum__municipio")
        .annotate(
            indice_filtro=INDICE,
            observaciones_sin_resolver=Count("observaciones", filter=Q(observaciones__estado__in=Observacion.NO_RESUELTAS), distinct=True),
        )
    )
    if convocatoria := params.get("convocatoria"):
        qs = qs.filter(convocatoria_id=convocatoria)
    if estado := params.get("estado"):
        qs = qs.filter(estado=estado)
    if desde := params.get("desde"):
        qs = qs.filter(confirmada_at__date__gte=desde)
    if hasta := params.get("hasta"):
        qs = qs.filter(confirmada_at__date__lte=hasta)
    if (minimo := params.get("indice_min")) not in (None, ""):
        qs = qs.filter(indice_filtro__gte=minimo)
    if (maximo := params.get("indice_max")) not in (None, ""):
        qs = qs.filter(indice_filtro__lte=maximo)
    if params.get("con_observaciones") == "true":
        qs = qs.filter(observaciones_sin_resolver__gt=0)
    if buscar := (params.get("buscar") or "").strip():
        # El CI está cifrado: se busca por coincidencia exacta con su hash.
        condicion = Q(aspirante__first_name__icontains=buscar) | Q(aspirante__last_name__icontains=buscar)
        if buscar.isdigit() and len(buscar) == 11:
            condicion |= Q(aspirante__ci_hash=crypto.hash_busqueda(buscar))
        qs = qs.filter(condicion)

    orden = {"indice": F("indice_filtro").desc(nulls_last=True), "nombre": "aspirante__first_name"}.get(params.get("orden"))
    return qs.order_by(orden or F("confirmada_at").desc(nulls_last=True), "pk")


def convocatoria_de(params):
    """La indicada o, si no, la más reciente abierta o cerrada. None si todavía no hay ninguna."""
    if convocatoria_id := params.get("convocatoria"):
        convocatoria = ConvocatoriaSolicitud.objects.filter(pk=convocatoria_id).first()
        if convocatoria is None:
            raise ErrorDeNegocio("La convocatoria no existe.")
        return convocatoria
    return ConvocatoriaSolicitud.objects.exclude(estado=ConvocatoriaSolicitud.Estado.BORRADOR).order_by(
        "-anio_academico", "-numero"
    ).first()


def estadisticas_vacias():
    """Antes de la primera convocatoria no es un error: simplemente no hay datos."""
    return {
        "convocatoria": None,
        "totales": {"solicitudes": 0, "plazas": 0, "por_estado": {e: 0 for e in E.values if e != E.BORRADOR}},
        "termometro": [],
        "por_carrera": [],
        "evolucion": [],
    }


def estadisticas(usuario, convocatoria):
    """RF-053: solicitudes frente al plan por carrera (termómetro), distribución por carrera y evolución diaria."""
    solicitudes = revision.solicitudes_visibles(usuario).filter(convocatoria=convocatoria)
    opciones = revision.opciones_de_su_entidad(usuario, SolicitudCarrera.objects.filter(solicitud__in=solicitudes))

    ofertas = ofertas_de(convocatoria).select_related("carrera", "facultad", "cum_fum")
    if not usuario.es_global:
        ofertas = ofertas.filter(facultad_id=usuario.facultad_id) if usuario.facultad_id else ofertas.filter(cum_fum_id=usuario.cum_fum_id)
    por_oferta = {
        fila["oferta"]: fila
        for fila in opciones.values("oferta").annotate(total=Count("pk"), primera=Count("pk", filter=Q(prioridad=1)))
    }
    termometro = sorted(
        (
            {
                "oferta": o.pk, "carrera": o.carrera.nombre, "entidad": str(o.entidad), "plazas": o.plazas_plan,
                "solicitudes": por_oferta.get(o.pk, {}).get("total", 0), "primera_opcion": por_oferta.get(o.pk, {}).get("primera", 0),
            }
            for o in ofertas
        ),
        key=lambda f: (f["carrera"], f["entidad"]),
    )

    por_carrera = {}
    for fila in termometro:
        carrera = por_carrera.setdefault(fila["carrera"], {"carrera": fila["carrera"], "plazas": 0, "solicitudes": 0, "primera_opcion": 0})
        for clave in ("plazas", "solicitudes", "primera_opcion"):
            carrera[clave] += fila[clave]

    evolucion = (
        solicitudes.filter(confirmada_at__isnull=False)
        .annotate(dia=TruncDate("confirmada_at"))
        .values("dia")
        .annotate(total=Count("pk"))
        .order_by("dia")
    )
    por_estado = dict(solicitudes.values_list("estado").annotate(total=Count("pk")))
    return {
        "convocatoria": {"id": convocatoria.pk, "anio_academico": convocatoria.anio_academico, "numero": convocatoria.numero},
        "totales": {
            "solicitudes": sum(por_estado.values()),
            "plazas": sum(f["plazas"] or 0 for f in termometro),
            "por_estado": {estado: por_estado.get(estado, 0) for estado in E.values if estado != E.BORRADOR},
        },
        "termometro": termometro,
        "por_carrera": sorted(por_carrera.values(), key=lambda f: -f["solicitudes"]),
        "evolucion": [{"dia": f["dia"], "total": f["total"]} for f in evolucion],
    }


def filas_exportacion(usuario, solicitudes):
    """Filas del Excel/PDF: una por solicitud, con solo las opciones que el usuario puede ver."""
    from .serializers import _carreras_visibles

    filas = []
    for s in solicitudes:
        perfil = s.aspirante.perfil_aspirante
        carreras = "; ".join(f"{c.prioridad}. {c.oferta.carrera.nombre} — {c.oferta.entidad}" for c in _carreras_visibles(s, usuario))
        filas.append([
            s.aspirante.nombre_completo, s.aspirante.ci, s.aspirante.celular, s.aspirante.email,
            perfil.indice_declarado, perfil.indice_validado, s.get_estado_display(), s.observaciones_sin_resolver,
            carreras, s.confirmada_at.astimezone().strftime("%d/%m/%Y %H:%M") if s.confirmada_at else "",
        ])
    return filas


COLUMNAS_EXPORTACION = [
    ("Aspirante", 30), ("CI", 14), ("Celular", 11), ("Email", 28), ("Índice declarado", 10), ("Índice validado", 10),
    ("Estado", 14), ("Observaciones sin resolver", 12), ("Carreras", 60), ("Confirmada", 17),
]
