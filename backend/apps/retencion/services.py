"""Política de retención de datos personales (RG-028, decisiones del cliente).

- No seleccionados (y aspirantes sin resultado): se anonimizan pasados
  `retencion_anios` (2) desde la publicación del último otorgamiento del año
  de su solicitud más reciente.
- Otorgados: conservación ampliada, `retencion_otorgados_anios` (5).
- Aspirantes que nunca confirmaron una solicitud: `retencion_anios` desde su
  último acceso o, si nunca entraron, desde el registro.
- Con un proceso todavía sin publicar (o una solicitud posterior), no se toca.
- Versiones antiguas de documentos: se borran al vencer `retencion_anios`; la
  vigente se conserva mientras el expediente siga sujeto a conservación. Al
  anonimizar se borran todas, incluida la vigente.
- Expresiones de interés: cierre de su convocatoria + `retencion_anios`.
- Anonimizar no borra: se conservan solicitudes, carreras, prioridades,
  estados, resultado, índice, estadísticas y snapshots.
- Los registros de auditoría no se alteran (son evidencia del sistema).
"""

import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import CharField, Max, Q, Value
from django.db.models.functions import Cast, Concat
from django.utils import timezone

from apps.aspirantes.models import DocumentoAspirante, PerfilAspirante
from apps.auditoria import services as auditoria
from apps.configuracion.services import parametros
from apps.interes.models import ExpresionInteres
from apps.notificaciones.models import Notificacion
from apps.otorgamiento.models import Otorgamiento, ResultadoOtorgamiento
from apps.prematricula.models import ArchivoPrematricula, ElementoPrematricula
from apps.roles.models import Rol
from apps.solicitudes.models import EventoHistorial, Solicitud
from apps.users.models import Usuario

from .models import RetencionEjecutada

NOMBRE_ANONIMO = "Aspirante anonimizado"
INTERESADO_ANONIMO = "Interesado anonimizado"


def sumar_anios(fecha, anios):
    try:
        return fecha.replace(year=fecha.year + anios)
    except ValueError:  # 29 de febrero
        return fecha.replace(year=fecha.year + anios, day=28)


@dataclass
class Plan:
    """Lo que haría una ejecución hoy. Se calcula igual para la vista previa y para ejecutar."""

    aspirantes: list = field(default_factory=list)  # Usuario a anonimizar
    solo_versiones: list = field(default_factory=list)  # Usuario a quienes solo se les borran versiones antiguas
    intereses: object = None  # QuerySet de ExpresionInteres

    def archivos(self):
        """(documentos del perfil, archivos de prematrícula, fotos) que se borrarían."""
        completos = [u.pk for u in self.aspirantes]
        parciales = [u.pk for u in self.solo_versiones]
        documentos = DocumentoAspirante.objects.filter(
            Q(perfil__usuario_id__in=completos) | Q(perfil__usuario_id__in=parciales, vigente=False)
        )
        prematricula = ArchivoPrematricula.objects.filter(
            Q(elemento__prematricula__aspirante_id__in=completos) | Q(elemento__prematricula__aspirante_id__in=parciales, vigente=False)
        )
        fotos = [u for u in self.aspirantes if u.foto]
        return documentos, prematricula, fotos


def _referencias():
    """Fecha de publicación del último otorgamiento de cada año académico."""
    return dict(
        Otorgamiento.objects.filter(estado=Otorgamiento.Estado.PUBLICADO)
        .values_list("convocatoria__anio_academico")
        .annotate(ultima=Max("publicado_at"))
    )


def _vencimientos(usuario, publicaciones, anios, anios_otorgados):
    """(fecha en que vence la retención base, fecha en que vence la de anonimización) o None si no aplica todavía."""
    ultima = (
        Solicitud.objects.filter(aspirante=usuario)
        .exclude(estado=Solicitud.Estado.BORRADOR)
        .select_related("convocatoria")
        .order_by("-convocatoria__anio_academico", "-convocatoria__numero")
        .first()
    )
    if ultima is None:
        referencia = (usuario.last_login or usuario.date_joined).date()
        return sumar_anios(referencia, anios), sumar_anios(referencia, anios)
    publicado = publicaciones.get(ultima.convocatoria.anio_academico)
    # Proceso sin publicar o todavía con convocatorias en marcha ese año: no se toca.
    if publicado is None or ultima.estado not in (Solicitud.Estado.OTORGADA, Solicitud.Estado.NO_SELECCIONADO):
        return None
    referencia = timezone.localtime(publicado).date()
    plazo = anios_otorgados if ultima.estado == Solicitud.Estado.OTORGADA else anios
    return sumar_anios(referencia, anios), sumar_anios(referencia, plazo)


def calcular(hoy=None):
    hoy = hoy or timezone.localdate()
    config = parametros()
    publicaciones = _referencias()
    plan = Plan()
    aspirantes = Usuario.objects.filter(rol__codigo=Rol.ASPIRANTE, anonimizado_at__isnull=True)
    for usuario in aspirantes:
        vencimientos = _vencimientos(usuario, publicaciones, config.retencion_anios, config.retencion_otorgados_anios)
        if vencimientos is None:
            continue
        base, anonimizacion = vencimientos
        if anonimizacion <= hoy:
            plan.aspirantes.append(usuario)
        elif base <= hoy:
            plan.solo_versiones.append(usuario)

    limite = sumar_anios(hoy, -config.retencion_anios)
    plan.intereses = ExpresionInteres.objects.filter(anonimizada_at__isnull=True, convocatoria__fecha_cierre__lte=limite)
    return plan


def _tamano_foto(usuario):
    try:
        return usuario.foto.size
    except (FileNotFoundError, OSError, ValueError):
        return 0


def previsualizar(hoy=None):
    plan = calcular(hoy)
    documentos, prematricula, fotos = plan.archivos()
    bytes_ = sum(documentos.values_list("tamano", flat=True)) + sum(prematricula.values_list("tamano", flat=True)) + sum(map(_tamano_foto, fotos))
    return {
        "aspirantes": len(plan.aspirantes),
        "intereses": plan.intereses.count(),
        "documentos": documentos.count() + prematricula.count() + len(fotos),
        "espacio_mb": round(Decimal(bytes_) / (1024 * 1024), 2),
        "solo_versiones_antiguas": len(plan.solo_versiones),
    }


def _borrar_archivos(nombres):
    transaction.on_commit(lambda: [default_storage.delete(n) for n in nombres if n])


def _anonimizar(usuario):
    """Quita los datos personales de un aspirante y desactiva su cuenta. Lo demás se conserva."""
    usuario.first_name, usuario.last_name = NOMBRE_ANONIMO.split(" ", 1)
    usuario.username = f"anon_{uuid.uuid4().hex}"
    usuario.email = usuario.ci = usuario.celular = ""
    usuario.foto = None
    usuario.is_active = False
    usuario.set_unusable_password()
    usuario.anonimizado_at = timezone.now()
    usuario.save()
    PerfilAspirante.objects.filter(usuario=usuario).update(centro_trabajo="")
    ElementoPrematricula.objects.filter(prematricula__aspirante=usuario).update(valor_texto="")
    ResultadoOtorgamiento.objects.filter(aspirante=usuario).update(aspirante_nombre=NOMBRE_ANONIMO)
    Notificacion.objects.filter(usuario=usuario).delete()
    # El historial guarda valores de datos y nombres de archivo: se vacían; el evento (qué y cuándo) se conserva.
    EventoHistorial.objects.filter(aspirante=usuario, tipo__in=[EventoHistorial.Tipo.DATOS, EventoHistorial.Tipo.DOCUMENTO]).update(
        antes=None, despues=None
    )


@transaction.atomic
def ejecutar(usuario=None, automatica=False, hoy=None):
    inicio = time.monotonic()
    plan = calcular(hoy)
    documentos, prematricula, fotos = plan.archivos()
    nombres = list(documentos.values_list("archivo", flat=True)) + list(prematricula.values_list("archivo", flat=True))
    nombres += [u.foto.name for u in fotos]
    bytes_ = sum(documentos.values_list("tamano", flat=True)) + sum(prematricula.values_list("tamano", flat=True)) + sum(map(_tamano_foto, fotos))
    total_archivos = len(nombres)
    documentos.delete()
    prematricula.delete()
    _borrar_archivos(nombres)

    for aspirante in plan.aspirantes:
        _anonimizar(aspirante)

    intereses = plan.intereses.update(
        nombre=INTERESADO_ANONIMO, ci="", celular="", email="", anonimizada_at=timezone.now(),
        # El hash debe seguir siendo único por oferta: se reemplaza por uno técnico, sin relación con el CI.
        ci_hash=Concat(Value("anonimizado-"), Cast("pk", CharField())),
    )
    ejecucion = RetencionEjecutada.objects.create(
        ejecutada_por=usuario, automatica=automatica,
        aspirantes_anonimizados=len(plan.aspirantes), intereses_anonimizados=intereses, documentos_eliminados=total_archivos,
        espacio_liberado_mb=round(Decimal(bytes_) / (1024 * 1024), 2),
        duracion_segundos=round(Decimal(time.monotonic() - inicio), 2),
    )
    auditoria.registrar(
        usuario=usuario, accion=f"ejecutar retención ({'automática' if automatica else 'manual'})", modulo="retencion",
        entidad_afectada="retencion", entidad_id=ejecucion.pk,
        detalle={
            "aspirantes": ejecucion.aspirantes_anonimizados, "intereses": ejecucion.intereses_anonimizados,
            "archivos": ejecucion.documentos_eliminados, "espacio_mb": str(ejecucion.espacio_liberado_mb),
        },
    )
    return ejecucion

