"""Dashboard principal: vista ejecutiva del proceso por rol (sección 9 del mockup, RF-030).

Cada sección aparece solo si el usuario tiene `ver` en ese módulo y se calcula
dentro de su ámbito: los roles globales ven todo, los locales su entidad.
Las alertas operativas son tarjetas de atención rápida, no notificaciones.
"""

from django.db.models import Count
from django.utils import timezone

from apps.convocatorias.models import ConvocatoriaSolicitud
from apps.core.ambito import filtrar_por_entidad
from apps.interes.models import ConvocatoriaInteres, ExpresionInteres
from apps.otorgamiento.models import Otorgamiento
from apps.plan_plazas.models import PlanEntidad, PlanPlazas
from apps.prematricula import services as prematricula
from apps.prematricula.models import Prematricula
from apps.roles.catalogo import APROBAR, EDITAR, GENERAR, PUBLICAR, VER
from apps.solicitudes import revision
from apps.solicitudes.models import Solicitud

# Una convocatoria abierta "está por cerrar" cuando le quedan estos días o menos.
DIAS_AVISO_CIERRE = 3


def _dias_hasta(fecha):
    return (fecha - timezone.localdate()).days


def _alerta(nivel, texto, enlace):
    return {"nivel": nivel, "texto": texto, "enlace": enlace}


def _interes(usuario, alertas):
    convocatoria = ConvocatoriaInteres.objects.filter(estado=ConvocatoriaInteres.Estado.ABIERTA).first() or ConvocatoriaInteres.objects.first()
    if convocatoria is None:
        return None
    expresiones = filtrar_por_entidad(
        ExpresionInteres.objects.filter(convocatoria=convocatoria), usuario, campo_facultad="oferta__facultad", campo_cum_fum="oferta__cum_fum"
    )
    if convocatoria.estado == ConvocatoriaInteres.Estado.ABIERTA and 0 <= (dias := _dias_hasta(convocatoria.fecha_cierre)) <= DIAS_AVISO_CIERRE:
        alertas.append(_alerta("aviso", f"La convocatoria de interés {convocatoria.anio_academico} cierra en {dias} día(s).", "/admin/interes"))
    return {
        "anio_academico": convocatoria.anio_academico, "estado": convocatoria.get_estado_display(),
        "fecha_cierre": convocatoria.fecha_cierre, "expresiones": expresiones.count(),
    }


def _plan(usuario, alertas):
    plan = PlanPlazas.objects.order_by("-anio_academico", "-created_at").first()
    if plan is None:
        return None
    datos = {"anio_academico": plan.anio_academico, "estado": plan.get_estado_display(), "id": plan.pk}
    entidades = filtrar_por_entidad(PlanEntidad.objects.filter(plan=plan), usuario)
    pendientes = entidades.exclude(estado=PlanEntidad.Estado.PROPUESTA_ENVIADA).count() if plan.estado == PlanPlazas.Estado.ENVIADO else 0
    datos["entidades_pendientes"] = pendientes
    if pendientes and usuario.tiene_permiso("plan_plazas", EDITAR):
        texto = (
            f"Tu entidad todavía no envió su propuesta del plan de plazas {plan.anio_academico}."
            if not usuario.es_global
            else f"{pendientes} entidad(es) todavía no enviaron su propuesta del plan de plazas {plan.anio_academico}."
        )
        alertas.append(_alerta("aviso", texto, f"/admin/plan-plazas/{plan.pk}"))
    return datos


def _convocatoria_solicitud():
    return ConvocatoriaSolicitud.objects.exclude(estado=ConvocatoriaSolicitud.Estado.BORRADOR).order_by("-anio_academico", "-numero").first()


def _solicitudes(usuario, alertas):
    convocatoria = _convocatoria_solicitud()
    if convocatoria is None:
        return None
    solicitudes = revision.solicitudes_visibles(usuario).filter(convocatoria=convocatoria)
    por_estado = dict(solicitudes.values_list("estado").annotate(n=Count("pk")))
    if convocatoria.estado == ConvocatoriaSolicitud.Estado.ABIERTA and 0 <= (dias := _dias_hasta(convocatoria.fecha_cierre)) <= DIAS_AVISO_CIERRE:
        alertas.append(_alerta("aviso", f"La convocatoria de solicitud {convocatoria.numero}.ª {convocatoria.anio_academico} cierra en {dias} día(s).", "/admin/convocatorias"))
    if usuario.tiene_permiso("solicitudes", EDITAR):
        if observadas := por_estado.get(Solicitud.Estado.OBSERVADA, 0):
            alertas.append(_alerta("atencion", f"{observadas} solicitud(es) observadas esperan la corrección del aspirante.", "/admin/solicitudes"))
        if pendientes := por_estado.get(Solicitud.Estado.PENDIENTE, 0):
            alertas.append(_alerta("info", f"{pendientes} solicitud(es) pendientes de revisión.", "/admin/solicitudes"))
    return {
        "convocatoria": f"{convocatoria.numero}.ª {convocatoria.anio_academico}",
        "estado_convocatoria": convocatoria.get_estado_display(),
        "fecha_cierre": convocatoria.fecha_cierre,
        "total": sum(por_estado.values()),
        "por_estado": {e: por_estado.get(e, 0) for e in Solicitud.Estado.values if e != Solicitud.Estado.BORRADOR},
    }


def _otorgamiento(usuario, alertas):
    convocatoria = _convocatoria_solicitud()
    if convocatoria is None:
        return None
    otorgamiento = Otorgamiento.objects.filter(convocatoria=convocatoria).first()
    if otorgamiento is None:
        if convocatoria.estado == ConvocatoriaSolicitud.Estado.CERRADA and usuario.tiene_permiso("otorgamiento", GENERAR):
            alertas.append(_alerta("atencion", f"La convocatoria {convocatoria.numero}.ª {convocatoria.anio_academico} cerró y falta generar el otorgamiento.", "/admin/otorgamiento"))
        return {"convocatoria": f"{convocatoria.numero}.ª {convocatoria.anio_academico}", "estado": "Sin generar", "otorgadas": None}
    if not usuario.es_global and not otorgamiento.publicado:
        return {"convocatoria": f"{convocatoria.numero}.ª {convocatoria.anio_academico}", "estado": "En elaboración", "otorgadas": None}
    etapa = {Otorgamiento.Estado.REVISION_CI: APROBAR, Otorgamiento.Estado.APROBACION: PUBLICAR}.get(otorgamiento.estado)
    if etapa and usuario.tiene_permiso("otorgamiento", etapa):
        alertas.append(_alerta("atencion", f"El otorgamiento {convocatoria.numero}.ª {convocatoria.anio_academico} está pendiente de tu aprobación.", "/admin/otorgamiento"))
    from apps.otorgamiento.services import resultados_visibles

    return {
        "convocatoria": f"{convocatoria.numero}.ª {convocatoria.anio_academico}",
        "estado": otorgamiento.get_estado_display(),
        "otorgadas": resultados_visibles(usuario, otorgamiento).filter(otorgada__isnull=False).count(),
    }


def _prematricula(usuario, alertas):
    expedientes = prematricula.visibles(usuario)
    if not expedientes.exists():
        return None
    por_estado = dict(expedientes.values_list("estado").annotate(n=Count("pk")))
    E = Prematricula.Estado
    if usuario.tiene_permiso("prematricula", EDITAR) and (completadas := por_estado.get(E.COMPLETADA, 0)):
        alertas.append(_alerta("info", f"{completadas} prematrícula(s) enviadas esperan revisión.", "/admin/prematricula"))
    if incompletas := por_estado.get(E.INCOMPLETA, 0):
        alertas.append(_alerta("atencion", f"{incompletas} prematrícula(s) quedaron incompletas al cierre.", "/admin/prematricula"))
    if correcciones := por_estado.get(E.CON_CORRECCIONES, 0):
        alertas.append(_alerta("aviso", f"{correcciones} prematrícula(s) con correcciones pendientes del aspirante.", "/admin/prematricula"))
    periodo = expedientes.order_by("-periodo__fecha_cierre").first().periodo
    if periodo.abierto and _dias_hasta(periodo.fecha_cierre) <= DIAS_AVISO_CIERRE:
        alertas.append(_alerta("aviso", f"La prematrícula cierra en {_dias_hasta(periodo.fecha_cierre)} día(s).", "/admin/prematricula"))
    return {"total": sum(por_estado.values()), "por_estado": {e: por_estado.get(e, 0) for e in E.values}, "fecha_cierre": periodo.fecha_cierre}


SECCIONES = {
    "interes": _interes,
    "plan_plazas": _plan,
    "solicitudes": _solicitudes,
    "otorgamiento": _otorgamiento,
    "prematricula": _prematricula,
}
ORDEN_NIVEL = {"atencion": 0, "aviso": 1, "info": 2}


def resumen(usuario):
    alertas = []
    secciones = {
        modulo: calcular(usuario, alertas) for modulo, calcular in SECCIONES.items() if usuario.tiene_permiso(modulo, VER)
    }
    return {
        "secciones": {m: datos for m, datos in secciones.items() if datos is not None},
        "alertas": sorted(alertas, key=lambda a: ORDEN_NIVEL[a["nivel"]]),
        "actualizado": timezone.now(),
    }

