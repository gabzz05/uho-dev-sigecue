from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.exceptions import ErrorDeNegocio
from apps.oferta.models import OfertaCarrera
from apps.plan_plazas.services import plan_vigente

from .models import ConvocatoriaSolicitud

E = ConvocatoriaSolicitud.Estado


def convocatoria_abierta():
    """La convocatoria que hoy acepta solicitudes, o None."""
    convocatoria = ConvocatoriaSolicitud.objects.filter(estado=E.ABIERTA).first()
    return convocatoria if convocatoria and convocatoria.acepta_solicitudes else None


def ofertas_de(convocatoria, con_restantes=True):
    """Carreras con plazas en el plan vigente del año, dentro de las entidades de la convocatoria.

    Desde la segunda convocatoria, solo las que conservan plazas: plan menos
    lo otorgado en las anteriores (RF-062).
    """
    qs = OfertaCarrera.objects.filter(anio_academico=convocatoria.anio_academico, plazas_plan__gt=0)
    if not convocatoria.para_todas_las_entidades:
        qs = qs.filter(Q(facultad__in=convocatoria.facultades.all()) | Q(cum_fum__in=convocatoria.cum_fums.all()))
    if con_restantes and convocatoria.numero > 1:
        from apps.otorgamiento.services import plazas_restantes

        sin_plazas = [oferta for oferta, plazas in plazas_restantes(convocatoria).items() if plazas <= 0]
        qs = qs.exclude(pk__in=sin_plazas)
    return qs


def siguiente_numero(anio_academico):
    ultima = ConvocatoriaSolicitud.objects.filter(anio_academico=anio_academico).order_by("-numero").first()
    if ultima is None:
        return 1
    if ultima.estado != E.CERRADA:
        raise ErrorDeNegocio(f"La convocatoria {ultima.numero} de {anio_academico} todavía no está cerrada.")
    # RF-062: la siguiente reparte las plazas restantes, que solo se conocen con el otorgamiento publicado.
    otorgamiento = getattr(ultima, "otorgamiento", None)
    if otorgamiento is None or not otorgamiento.publicado:
        raise ErrorDeNegocio(f"El otorgamiento de la convocatoria {ultima.numero} de {anio_academico} todavía no está publicado.")
    return ultima.numero + 1


def crear(datos, actor):
    facultades = datos.pop("facultades", [])
    cum_fums = datos.pop("cum_fums", [])
    try:
        with transaction.atomic():
            convocatoria = ConvocatoriaSolicitud.objects.create(
                **datos, numero=siguiente_numero(datos["anio_academico"]), created_by=actor
            )
            convocatoria.facultades.set(facultades)
            convocatoria.cum_fums.set(cum_fums)
    except IntegrityError:
        raise ErrorDeNegocio("Ya existe esa convocatoria para el año académico.")
    return convocatoria


@transaction.atomic
def abrir(convocatoria):
    convocatoria = ConvocatoriaSolicitud.objects.select_for_update().get(pk=convocatoria.pk)
    if convocatoria.estado != E.BORRADOR:
        raise ErrorDeNegocio("Solo se puede abrir una convocatoria en borrador.")
    if convocatoria.fecha_cierre < timezone.localdate():
        raise ErrorDeNegocio("La fecha de cierre ya pasó. Corrígela antes de abrir la convocatoria.")
    if plan_vigente(convocatoria.anio_academico) is None:
        raise ErrorDeNegocio(f"El plan de plazas {convocatoria.anio_academico} todavía no está publicado.")
    if not ofertas_de(convocatoria).exists():
        if convocatoria.numero > 1 and ofertas_de(convocatoria, con_restantes=False).exists():
            raise ErrorDeNegocio("No quedan plazas libres en estas entidades: se otorgaron todas en las convocatorias anteriores.")
        raise ErrorDeNegocio("Las entidades seleccionadas no tienen plazas en el plan de plazas publicado.")
    if ConvocatoriaSolicitud.objects.filter(estado=E.ABIERTA).exists():
        raise ErrorDeNegocio("Ya hay otra convocatoria de solicitud abierta. Ciérrala primero.")

    convocatoria.estado = E.ABIERTA
    convocatoria.save(update_fields=["estado"])
    if convocatoria.numero == 1:
        # RF-041. En la segunda convocatoria se avisa a los no seleccionados (RF-061).
        from .tasks import notificar_interesados

        transaction.on_commit(lambda: notificar_interesados.delay(convocatoria.pk))
    return convocatoria


@transaction.atomic
def cerrar(convocatoria):
    convocatoria = ConvocatoriaSolicitud.objects.select_for_update().get(pk=convocatoria.pk)
    if convocatoria.estado != E.ABIERTA:
        raise ErrorDeNegocio("Solo se puede cerrar una convocatoria abierta.")
    convocatoria.estado = E.CERRADA
    convocatoria.save(update_fields=["estado"])
    return convocatoria


def cerrar_vencidas():
    """RF-043: cierra las convocatorias abiertas cuya fecha de cierre ya pasó."""
    return ConvocatoriaSolicitud.objects.filter(estado=E.ABIERTA, fecha_cierre__lt=timezone.localdate()).update(estado=E.CERRADA)
