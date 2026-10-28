from datetime import timedelta

from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from apps.aspirantes.models import DocumentoAspirante, TipoDocumento
from apps.core.exceptions import ErrorDeNegocio
from apps.core.validators import EXTENSION
from apps.notificaciones.services import notificar
from apps.otorgamiento.models import Otorgamiento
from apps.roles.catalogo import CONFIGURAR, EDITAR

from .models import MAX_TOTAL_MB, MAX_VERSIONES, ArchivoPrematricula, CampoPrematricula, ElementoPrematricula, PeriodoPrematricula, Prematricula

E = Prematricula.Estado
R = ElementoPrematricula.Revision
MODULO = "prematricula"
# Estados en los que el aspirante todavía tiene algo que hacer (reciben los recordatorios).
POR_COMPLETAR = (E.PENDIENTE, E.BORRADOR, E.CON_CORRECCIONES)


# --- Período ------------------------------------------------------------------


@transaction.atomic
def configurar_periodo(usuario, otorgamiento, fecha_inicio, fecha_cierre):
    """Fija (o corrige) el período de un otorgamiento publicado y crea el expediente de cada otorgado."""
    if not usuario.tiene_permiso(MODULO, CONFIGURAR):
        raise ErrorDeNegocio("El período de prematrícula lo configura la Secretaría General.")
    otorgamiento = Otorgamiento.objects.select_for_update().get(pk=otorgamiento.pk)
    if not otorgamiento.publicado:
        raise ErrorDeNegocio("La prematrícula se abre cuando el otorgamiento está publicado.")
    if fecha_cierre < fecha_inicio:
        raise ErrorDeNegocio("La fecha de cierre no puede ser anterior a la de inicio.")
    if fecha_cierre < timezone.localdate():
        raise ErrorDeNegocio("La fecha de cierre ya pasó.")

    periodo = PeriodoPrematricula.objects.select_for_update().filter(otorgamiento=otorgamiento).first()
    if periodo is None:
        periodo = PeriodoPrematricula.objects.create(
            otorgamiento=otorgamiento, fecha_inicio=fecha_inicio, fecha_cierre=fecha_cierre, configurado_por=usuario
        )
    else:
        if periodo.cerrado:
            raise ErrorDeNegocio("El período de prematrícula ya cerró.")
        periodo.fecha_inicio, periodo.fecha_cierre = fecha_inicio, fecha_cierre
        periodo.save(update_fields=["fecha_inicio", "fecha_cierre"])
    # El listado público de resultados se ve hasta el cierre de la prematrícula.
    Otorgamiento.objects.filter(pk=otorgamiento.pk).update(publico_hasta=fecha_cierre)

    for resultado in otorgamiento.resultados.filter(otorgada__isnull=False).select_related("aspirante"):
        prematricula, _ = Prematricula.objects.get_or_create(resultado=resultado, defaults={"periodo": periodo, "aspirante": resultado.aspirante})
        sincronizar_elementos(prematricula)
    if periodo.abierto and not periodo.aviso_apertura_enviado:
        avisar_apertura(periodo)
    return periodo


def sincronizar_elementos(prematricula):
    """Crea los elementos que falten: documentos obligatorios del perfil y campos activos (RF-065, RF-066)."""
    if prematricula.estado == E.APROBADA:
        return
    existentes_doc = set(prematricula.elementos.filter(tipo_documento__isnull=False).values_list("tipo_documento_id", flat=True))
    existentes_campo = set(prematricula.elementos.filter(campo__isnull=False).values_list("campo_id", flat=True))
    nuevos = [
        ElementoPrematricula(prematricula=prematricula, tipo_documento=t)
        for t in TipoDocumento.objects.filter(activo=True, obligatorio=True).exclude(pk__in=existentes_doc)
    ] + [
        ElementoPrematricula(prematricula=prematricula, campo=c)
        for c in CampoPrematricula.objects.filter(activo=True).exclude(pk__in=existentes_campo)
    ]
    ElementoPrematricula.objects.bulk_create(nuevos)


def _contexto(prematricula):
    resultado = prematricula.resultado
    return {"carrera": resultado.carrera, "entidad": resultado.entidad, "fecha_cierre": prematricula.periodo.fecha_cierre.strftime("%d/%m/%Y")}


def _avisar(prematriculas, plantilla, extra=None):
    prematriculas = list(prematriculas.select_related("aspirante", "resultado", "periodo"))
    por_aspirante = {p.aspirante_id: p for p in prematriculas}
    notificar([p.aspirante for p in prematriculas], plantilla, lambda u: _contexto(por_aspirante[u.pk]) | (extra or {}))
    return len(prematriculas)


def avisar_apertura(periodo):
    _avisar(periodo.prematriculas.all(), "prematricula_abierta")
    PeriodoPrematricula.objects.filter(pk=periodo.pk).update(aviso_apertura_enviado=True)


def tarea_diaria(hoy=None):
    """Avisos de apertura, recordatorios a 5 y 1 días del cierre (RF-070) y paso a Incompleta tras el cierre."""
    hoy = hoy or timezone.localdate()
    resumen = {"aperturas": 0, "recordatorios": 0, "incompletas": 0}
    for periodo in PeriodoPrematricula.objects.filter(fecha_cierre__gte=hoy - timedelta(days=1)):
        if periodo.fecha_inicio <= hoy <= periodo.fecha_cierre and not periodo.aviso_apertura_enviado:
            avisar_apertura(periodo)
            resumen["aperturas"] += 1
        dias = (periodo.fecha_cierre - hoy).days
        for faltan, campo in ((5, "recordatorio_5_enviado"), (1, "recordatorio_1_enviado")):
            if dias == faltan and not getattr(periodo, campo) and periodo.fecha_inicio <= hoy:
                resumen["recordatorios"] += _avisar(periodo.prematriculas.filter(estado__in=POR_COMPLETAR), "prematricula_recordatorio", {"dias": faltan})
                PeriodoPrematricula.objects.filter(pk=periodo.pk).update(**{campo: True})
    resumen["incompletas"] = Prematricula.objects.filter(periodo__fecha_cierre__lt=hoy, estado__in=(E.PENDIENTE, E.BORRADOR)).update(
        estado=E.INCOMPLETA
    )
    return resumen


# --- Estado de los elementos ----------------------------------------------------


def documento_vigente(prematricula, tipo_documento_id):
    return DocumentoAspirante.objects.filter(
        perfil__usuario_id=prematricula.aspirante_id, tipo_id=tipo_documento_id, vigente=True
    ).first()


def tiene_valor(elemento):
    if elemento.tipo_documento_id:
        return documento_vigente(elemento.prematricula, elemento.tipo_documento_id) is not None
    if elemento.campo.tipo == CampoPrematricula.Tipo.TEXTO:
        return bool(elemento.valor_texto.strip())
    return elemento.archivos.filter(vigente=True).exists()


def requerido(elemento):
    return bool(elemento.tipo_documento_id) or elemento.campo.requerido


def faltantes(prematricula):
    """Elementos requeridos sin entregar (RF-068, RF-071)."""
    return [e for e in prematricula.elementos.select_related("campo", "tipo_documento") if requerido(e) and not tiene_valor(e)]


def puede_editar_elemento(prematricula, elemento):
    """Lo aprobado no se toca. Con el período abierto, el resto; tras el cierre, solo lo rechazado (desbloqueo selectivo)."""
    if elemento.revision == R.APROBADO or prematricula.estado in (E.APROBADA, E.COMPLETADA):
        return False
    # Los documentos del perfil se reutilizan: solo se vuelven a pedir si la entidad los rechaza.
    if elemento.tipo_documento_id and elemento.revision != R.RECHAZADO:
        return False
    periodo = prematricula.periodo
    if periodo.abierto:
        return prematricula.estado in POR_COMPLETAR
    if periodo.cerrado:
        return prematricula.estado == E.CON_CORRECCIONES and elemento.revision == R.RECHAZADO
    return False  # todavía no empezó


def documentos_a_corregir(usuario):
    """Documentos del perfil que el aspirante puede sustituir aunque su perfil esté congelado.

    Solo los que la entidad rechazó en la prematrícula: si no, se reutiliza la versión vigente.
    """
    elementos = ElementoPrematricula.objects.filter(
        prematricula__aspirante=usuario, tipo_documento__isnull=False, revision=R.RECHAZADO
    ).select_related("prematricula__periodo")
    return {e.tipo_documento_id for e in elementos if puede_editar_elemento(e.prematricula, e)}


def documento_sustituido(usuario, tipo_documento):
    """El aspirante subió una versión nueva de un documento del perfil: vuelve a quedar pendiente de revisión."""
    ElementoPrematricula.objects.filter(
        prematricula__aspirante=usuario, tipo_documento=tipo_documento, revision=R.RECHAZADO
    ).exclude(prematricula__estado=E.APROBADA).update(revision=R.PENDIENTE)
    Prematricula.objects.filter(aspirante=usuario, estado=E.PENDIENTE).update(estado=E.BORRADOR)


# --- Aspirante -------------------------------------------------------------------


def _bloquear(prematricula):
    return Prematricula.objects.select_for_update(of=("self",)).select_related("periodo", "resultado").get(pk=prematricula.pk)


def _exigir_editable(prematricula, elemento):
    if not puede_editar_elemento(prematricula, elemento):
        if prematricula.periodo.fecha_inicio > timezone.localdate():
            raise ErrorDeNegocio(f"La prematrícula abre el {prematricula.periodo.fecha_inicio:%d/%m/%Y}.")
        raise ErrorDeNegocio(f"«{elemento.nombre}» ya no se puede modificar.")


def _modificado(prematricula, elemento):
    if elemento.revision == R.RECHAZADO:
        elemento.revision = R.PENDIENTE
        elemento.save(update_fields=["revision"])
    if prematricula.estado == E.PENDIENTE:
        prematricula.estado = E.BORRADOR
        prematricula.save(update_fields=["estado", "updated_at"])


@transaction.atomic
def guardar_texto(prematricula, elemento, valor):
    prematricula = _bloquear(prematricula)
    if elemento.campo is None or elemento.campo.tipo != CampoPrematricula.Tipo.TEXTO:
        raise ErrorDeNegocio("Ese elemento no es un campo de texto.")
    _exigir_editable(prematricula, elemento)
    elemento.valor_texto = valor.strip()
    elemento.save(update_fields=["valor_texto"])
    _modificado(prematricula, elemento)
    return elemento


def cuota_usada(aspirante):
    vigentes = ArchivoPrematricula.objects.filter(elemento__prematricula__aspirante=aspirante, vigente=True)
    return sum(vigentes.values_list("tamano", flat=True))


@transaction.atomic
def subir_archivo(prematricula, elemento, archivo, formato):
    prematricula = _bloquear(prematricula)
    if elemento.campo is None or elemento.campo.tipo == CampoPrematricula.Tipo.TEXTO:
        raise ErrorDeNegocio("Ese elemento no admite archivos. Los documentos del perfil se sustituyen desde el perfil.")
    if elemento.campo.tipo == CampoPrematricula.Tipo.IMAGEN and formato not in ("JPEG", "PNG"):
        raise ErrorDeNegocio(f"«{elemento.campo.nombre}» debe ser una imagen JPG o PNG.")
    _exigir_editable(prematricula, elemento)

    versiones = elemento.archivos.all()
    anterior = versiones.filter(vigente=True).first()
    usada = cuota_usada(prematricula.aspirante) - (anterior.tamano if anterior else 0)
    if usada + archivo.size > MAX_TOTAL_MB * 1024 * 1024:
        libre = max(MAX_TOTAL_MB * 1024 * 1024 - usada, 0) / (1024 * 1024)
        raise ErrorDeNegocio(f"Superarías el límite de {MAX_TOTAL_MB} MB de la prematrícula. Te quedan {libre:.1f} MB libres.")

    ultima = versiones.order_by("-version").first()
    versiones.filter(vigente=True).update(vigente=False)
    nuevo = ArchivoPrematricula(
        elemento=elemento, version=ultima.version + 1 if ultima else 1, formato=formato,
        tamano=archivo.size, nombre_original=(archivo.name or "archivo")[:255],
    )
    nuevo.archivo.save(f"archivo.{EXTENSION[formato]}", archivo, save=False)
    nuevo.save()
    for sobrante in list(elemento.archivos.order_by("-version")[MAX_VERSIONES:]):
        nombre = sobrante.archivo.name
        sobrante.delete()
        transaction.on_commit(lambda nombre=nombre: default_storage.delete(nombre))
    _modificado(prematricula, elemento)
    return nuevo


@transaction.atomic
def enviar(prematricula):
    """El aspirante da por completa la prematrícula (o reenvía tras corregir)."""
    prematricula = _bloquear(prematricula)
    periodo = prematricula.periodo
    if prematricula.estado not in POR_COMPLETAR:
        raise ErrorDeNegocio("Tu prematrícula no está pendiente de envío.")
    if not periodo.abierto and not (periodo.cerrado and prematricula.estado == E.CON_CORRECCIONES):
        raise ErrorDeNegocio("La prematrícula no está abierta.")
    if pendientes := faltantes(prematricula):
        raise ErrorDeNegocio("Falta entregar: " + ", ".join(e.nombre for e in pendientes) + ".")
    if rechazados := list(prematricula.elementos.filter(revision=R.RECHAZADO)):
        raise ErrorDeNegocio("Corrige antes: " + ", ".join(e.nombre for e in rechazados) + ".")
    prematricula.estado = E.COMPLETADA
    prematricula.enviada_at = timezone.now()
    prematricula.save(update_fields=["estado", "enviada_at", "updated_at"])
    return prematricula


# --- Revisión de la entidad -------------------------------------------------------


def visibles(usuario):
    """Expedientes del ámbito: los globales, todos; cada entidad, los de las plazas otorgadas en ella."""
    qs = Prematricula.objects.select_related("periodo__otorgamiento__convocatoria", "resultado__otorgada__oferta", "aspirante")
    if usuario.es_global:
        return qs
    if usuario.facultad_id:
        return qs.filter(resultado__otorgada__oferta__facultad_id=usuario.facultad_id)
    if usuario.cum_fum_id:
        return qs.filter(resultado__otorgada__oferta__cum_fum_id=usuario.cum_fum_id)
    return qs.none()


def puede_revisar(usuario, prematricula):
    return usuario.tiene_permiso(MODULO, EDITAR) and visibles(usuario).filter(pk=prematricula.pk).exists()


def _exigir_revisable(usuario, prematricula):
    if not puede_revisar(usuario, prematricula):
        raise ErrorDeNegocio("No puedes revisar esta prematrícula.")
    if prematricula.estado != E.COMPLETADA:
        raise ErrorDeNegocio("Solo se revisa una prematrícula enviada por el aspirante.")


@transaction.atomic
def revisar_elemento(usuario, prematricula, elemento, revision, observacion=""):
    prematricula = _bloquear(prematricula)
    _exigir_revisable(usuario, prematricula)
    if elemento.prematricula_id != prematricula.pk:
        raise ErrorDeNegocio("Ese elemento no pertenece a esta prematrícula.")
    if revision == R.RECHAZADO and not observacion.strip():
        raise ErrorDeNegocio("Explica qué hay que corregir.")
    if not tiene_valor(elemento):
        raise ErrorDeNegocio(f"«{elemento.nombre}» no se entregó.")
    elemento.revision = revision
    elemento.observacion = observacion.strip() if revision == R.RECHAZADO else ""
    elemento.revisado_por = usuario
    elemento.revisado_at = timezone.now()
    if elemento.tipo_documento_id:
        elemento.documento_revisado = documento_vigente(prematricula, elemento.tipo_documento_id)
    elemento.save()
    return elemento


@transaction.atomic
def solicitar_correcciones(usuario, prematricula):
    """RF-069: "rechazar" = pedir correcciones. Nunca hace perder la plaza."""
    prematricula = _bloquear(prematricula)
    _exigir_revisable(usuario, prematricula)
    rechazados = list(prematricula.elementos.filter(revision=R.RECHAZADO).select_related("campo", "tipo_documento"))
    if not rechazados:
        raise ErrorDeNegocio("Marca como rechazado lo que hay que corregir antes de pedir correcciones.")
    prematricula.estado = E.CON_CORRECCIONES
    prematricula.save(update_fields=["estado", "updated_at"])
    correcciones = "\n".join(f"- {e.nombre}: {e.observacion}" for e in rechazados)
    _avisar(Prematricula.objects.filter(pk=prematricula.pk), "prematricula_correccion", {"correcciones": correcciones})
    return prematricula


@transaction.atomic
def aprobar(usuario, prematricula):
    prematricula = _bloquear(prematricula)
    _exigir_revisable(usuario, prematricula)
    elementos = list(prematricula.elementos.select_related("campo", "tipo_documento"))
    sin_aprobar = [e for e in elementos if requerido(e) and e.revision != R.APROBADO]
    rechazados = [e for e in elementos if e.revision == R.RECHAZADO]
    if sin_aprobar or rechazados:
        raise ErrorDeNegocio("Para aprobar, todos los requeridos deben estar aprobados: " + ", ".join(e.nombre for e in sin_aprobar + rechazados) + ".")
    prematricula.estado = E.APROBADA
    prematricula.fecha_aprobacion = timezone.now()
    prematricula.aprobado_por = usuario
    prematricula.save(update_fields=["estado", "fecha_aprobacion", "aprobado_por", "updated_at"])
    _avisar(Prematricula.objects.filter(pk=prematricula.pk), "prematricula_aprobada")
    return prematricula


def puede_descargar(usuario, prematricula):
    """El aspirante, o el personal con `solicitudes.documentos_descargar` de la entidad de la plaza (o global)."""
    if usuario.pk == prematricula.aspirante_id:
        return True
    from apps.roles.catalogo import DESCARGAR_DOCUMENTOS

    return usuario.tiene_permiso("solicitudes", DESCARGAR_DOCUMENTOS) and visibles(usuario).filter(pk=prematricula.pk).exists()


def filtrar_faltante(qs, campo_id=None, tipo_documento_id=None):
    """RF-071: expedientes a los que les falta un campo o documento concreto."""
    if campo_id:
        campo = CampoPrematricula.objects.get(pk=campo_id)
        con_valor = ElementoPrematricula.objects.filter(campo=campo)
        con_valor = con_valor.exclude(valor_texto="") if campo.tipo == CampoPrematricula.Tipo.TEXTO else con_valor.filter(archivos__vigente=True)
        return qs.exclude(pk__in=con_valor.values("prematricula"))
    if tipo_documento_id:
        con_documento = DocumentoAspirante.objects.filter(tipo_id=tipo_documento_id, vigente=True).values("perfil__usuario")
        return qs.exclude(aspirante__in=con_documento)
    return qs

