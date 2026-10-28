from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.core import crypto
from apps.core.ambito import es_de_su_entidad
from apps.core.exceptions import ErrorDeNegocio
from apps.oferta.models import OfertaCarrera

from .models import ConvocatoriaInteres, ExpresionInteres


def estadisticas(expresiones):
    """RF-029 sobre las expresiones ya filtradas y dentro del ámbito del usuario (RF-030).

    La distribución territorial se calcula por el **municipio de la entidad
    ofertante**: la expresión de interés no guarda el municipio de la persona.
    """
    from django.db.models import Count
    from django.db.models.functions import Coalesce, TruncDate

    from apps.nomencladores.models import Municipio

    def contar(valores):
        return expresiones.values(*valores).annotate(total=Count("pk")).order_by("-total")

    por_entidad = [
        {"entidad": f["oferta__facultad__nombre"] or f["oferta__cum_fum__nombre"], "total": f["total"]}
        for f in contar(["oferta__facultad__nombre", "oferta__cum_fum__nombre"])
    ]
    por_municipio = dict(
        expresiones.annotate(municipio=Coalesce("oferta__facultad__municipio", "oferta__cum_fum__municipio"))
        .values_list("municipio")
        .annotate(total=Count("pk"))
    )
    return {
        "total": expresiones.count(),
        "por_carrera": [{"carrera": f["oferta__carrera__nombre"], "total": f["total"]} for f in contar(["oferta__carrera__nombre"])],
        "por_entidad": sorted(por_entidad, key=lambda f: (-f["total"], f["entidad"])),
        "evolucion": [
            {"dia": f["dia"], "total": f["total"]}
            for f in expresiones.annotate(dia=TruncDate("created_at")).values("dia").annotate(total=Count("pk")).order_by("dia")
        ],
        # Los 14 municipios, también los que no tienen interés, para pintar el mapa completo.
        "por_municipio": [
            {"municipio": m.pk, "nombre": m.nombre, "total": por_municipio.get(m.pk, 0)} for m in Municipio.objects.order_by("nombre")
        ],
    }


def convocatoria_abierta():
    """La convocatoria que hoy acepta expresiones de interés, o None."""
    convocatoria = ConvocatoriaInteres.objects.filter(estado=ConvocatoriaInteres.Estado.ABIERTA).first()
    return convocatoria if convocatoria and convocatoria.acepta_interes else None


# --- Ciclo de vida de la convocatoria (RF-026) --------------------------------

@transaction.atomic
def abrir(convocatoria):
    # Relee con bloqueo: la instancia puede estar desactualizada y dos aperturas no deben pisarse.
    convocatoria = ConvocatoriaInteres.objects.select_for_update().get(pk=convocatoria.pk)
    if convocatoria.estado != ConvocatoriaInteres.Estado.BORRADOR:
        raise ErrorDeNegocio("Solo se puede abrir una convocatoria en borrador.")
    if convocatoria.fecha_cierre < timezone.localdate():
        raise ErrorDeNegocio("La fecha de cierre ya pasó. Corrígela antes de abrir la convocatoria.")
    if not OfertaCarrera.objects.filter(anio_academico=convocatoria.anio_academico).exists():
        raise ErrorDeNegocio("Agrega al menos una carrera a la oferta antes de abrir la convocatoria.")
    if ConvocatoriaInteres.objects.filter(estado=ConvocatoriaInteres.Estado.ABIERTA).exists():
        raise ErrorDeNegocio("Ya hay otra convocatoria de interés abierta. Ciérrala primero.")
    convocatoria.estado = ConvocatoriaInteres.Estado.ABIERTA
    convocatoria.save(update_fields=["estado"])
    return convocatoria


@transaction.atomic
def cerrar(convocatoria):
    convocatoria = ConvocatoriaInteres.objects.select_for_update().get(pk=convocatoria.pk)
    if convocatoria.estado != ConvocatoriaInteres.Estado.ABIERTA:
        raise ErrorDeNegocio("Solo se puede cerrar una convocatoria abierta.")
    convocatoria.estado = ConvocatoriaInteres.Estado.CERRADA
    convocatoria.save(update_fields=["estado"])
    return convocatoria


def cerrar_vencidas():
    """Cierra las convocatorias abiertas cuya fecha de cierre ya pasó. Devuelve cuántas."""
    return ConvocatoriaInteres.objects.filter(
        estado=ConvocatoriaInteres.Estado.ABIERTA, fecha_cierre__lt=timezone.localdate()
    ).update(estado=ConvocatoriaInteres.Estado.CERRADA)


# --- Oferta (RF-027, RF-028) --------------------------------------------------

def agregar_oferta(convocatoria, carrera, facultad, cum_fum, actor):
    """La CI asigna carreras a cualquier entidad; cada entidad agrega carreras a la suya."""
    if not convocatoria.editable:
        raise ErrorDeNegocio("La convocatoria está cerrada: su oferta ya no se puede modificar.")
    if not actor.es_global and facultad is None and cum_fum is None:
        facultad, cum_fum = actor.facultad, actor.cum_fum
    if (facultad is None) == (cum_fum is None):
        raise ErrorDeNegocio("Indica una Facultad o un CUM/FUM (solo uno).")
    if not es_de_su_entidad(actor, facultad, cum_fum):
        raise ErrorDeNegocio("Solo puedes agregar carreras a la oferta de tu propia entidad.")
    if not carrera.activo:
        raise ErrorDeNegocio("La carrera está desactivada en el catálogo.")
    try:
        with transaction.atomic():
            return OfertaCarrera.objects.create(
                carrera=carrera, facultad=facultad, cum_fum=cum_fum, anio_academico=convocatoria.anio_academico,
                asignada_por_ci=actor.es_global, creada_por=actor,
            )
    except IntegrityError:
        raise ErrorDeNegocio("Esa carrera ya está en la oferta de esta entidad para este año.")


def quitar_oferta(oferta, actor):
    convocatoria = ConvocatoriaInteres.objects.filter(anio_academico=oferta.anio_academico).first()
    if convocatoria and not convocatoria.editable:
        raise ErrorDeNegocio("La convocatoria está cerrada: su oferta ya no se puede modificar.")
    if not actor.es_global and oferta.asignada_por_ci:
        raise ErrorDeNegocio("Esta carrera la asignó la Comisión de Ingreso: tu entidad no puede quitarla.")
    try:
        oferta.delete()
    except ProtectedError:
        raise ErrorDeNegocio("Esta carrera ya tiene expresiones de interés y no se puede quitar de la oferta.")


# --- Expresión de interés (RF-021, RF-022) ------------------------------------

def registrar_interes(oferta, nombre, ci, celular, email):
    convocatoria = convocatoria_abierta()
    if convocatoria is None or oferta.anio_academico != convocatoria.anio_academico:
        raise ErrorDeNegocio("La convocatoria de interés para esta carrera no está abierta.")
    if ExpresionInteres.objects.filter(oferta=oferta, ci_hash=crypto.hash_busqueda(ci)).exists():
        raise ErrorDeNegocio("Ya registraste tu interés en esta carrera para este año.")

    try:
        with transaction.atomic():
            expresion = ExpresionInteres.objects.create(
                convocatoria=convocatoria, oferta=oferta, nombre=nombre, ci=ci, celular=celular, email=email
            )
    except IntegrityError:  # Dos envíos simultáneos del mismo CI.
        raise ErrorDeNegocio("Ya registraste tu interés en esta carrera para este año.")

    from .tasks import enviar_confirmacion

    transaction.on_commit(lambda: enviar_confirmacion.delay(expresion.pk))
    return expresion
