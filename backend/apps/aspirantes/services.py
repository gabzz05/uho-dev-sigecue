from django.core.files.storage import default_storage
from django.db import transaction

from apps.core.exceptions import ErrorDeNegocio
from apps.core.validators import EXTENSION
from apps.roles.catalogo import DESCARGAR_DOCUMENTOS

from .models import MAX_TOTAL_MB, MAX_VERSIONES, DocumentoAspirante, PerfilAspirante, TipoDocumento

MENSAJE_BLOQUEADO = "Tu perfil está congelado: la convocatoria en la que presentaste tu solicitud ya cerró."

# Requisitos del perfil completo, en el orden en que se muestran al aspirante.
REQUISITOS = {
    "datos_personales": "Datos personales",
    "correo_validado": "Correo validado",
    "privacidad": "Política de privacidad aceptada",
    "foto": "Foto de perfil",
    "centro_trabajo": "Centro de trabajo",
    "indice": "Índice académico",
    "documentos": "Documentos obligatorios",
    "carreras": "Al menos una carrera seleccionada",
}


def perfil_de(usuario):
    return PerfilAspirante.objects.get_or_create(usuario=usuario)[0]


def _tamano(archivo):
    try:
        return archivo.size if archivo else 0
    except (FileNotFoundError, OSError):
        return 0


def requisitos_perfil(perfil):
    """Qué cumple el perfil y qué no (RF-046). Es la fuente de verdad de `perfil_completo`."""
    from apps.solicitudes.services import tiene_carreras

    usuario = perfil.usuario
    vigentes = set(perfil.documentos.filter(vigente=True).values_list("tipo_id", flat=True))
    obligatorios = set(TipoDocumento.objects.filter(activo=True, obligatorio=True).values_list("id", flat=True))
    return {
        "datos_personales": all([usuario.first_name, usuario.last_name, usuario.ci, usuario.email, usuario.celular]),
        "correo_validado": usuario.email_verificado,
        "privacidad": usuario.privacidad_aceptada_at is not None,
        "foto": bool(usuario.foto),
        "centro_trabajo": bool(perfil.centro_trabajo.strip()),
        "indice": perfil.indice_declarado is not None,
        "documentos": obligatorios <= vigentes,
        "carreras": tiene_carreras(usuario),
    }


def calcular_perfil_completo(perfil, requisitos=None):
    return all((requisitos or requisitos_perfil(perfil)).values())


def listo_para_carreras(perfil, requisitos=None):
    """RF-046: para elegir carreras hace falta todo el perfil salvo, claro, las carreras."""
    requisitos = requisitos or requisitos_perfil(perfil)
    return all(cumple for clave, cumple in requisitos.items() if clave != "carreras")


def actualizar_perfil_completo(perfil):
    """Recalcula la caché `perfil_completo`. Llamarla tras cada cambio del perfil, documentos, foto o carreras."""
    completo = calcular_perfil_completo(perfil)
    if completo != perfil.perfil_completo:
        PerfilAspirante.objects.filter(pk=perfil.pk).update(perfil_completo=completo)
        perfil.perfil_completo = completo
    return completo


def perfil_bloqueado(usuario):
    """El perfil se congela junto con la solicitud.

    Lo está si tiene una solicitud confirmada en una convocatoria que ya no
    acepta solicitudes, salvo que su resultado sea "no seleccionado" (puede
    volver a solicitar en la siguiente convocatoria, RF-062).
    """
    from apps.solicitudes.models import Solicitud

    E = Solicitud.Estado
    solicitudes = (
        Solicitud.objects.filter(aspirante=usuario)
        .exclude(estado__in=[E.BORRADOR, E.NO_SELECCIONADO])
        .select_related("convocatoria")
    )
    return any(not s.convocatoria.acepta_solicitudes for s in solicitudes)


def puede_editar(usuario, objetivo, tipo_documento_id=None):
    """¿Puede el aspirante cambiar ese elemento del perfil?

    Con el perfil congelado, solo lo que tiene una observación por corregir
    (desbloqueo selectivo): ese documento, el índice, el centro de trabajo o la foto.
    """
    if not perfil_bloqueado(usuario):
        return True
    from apps.solicitudes.revision import objetivos_a_corregir

    return (objetivo, tipo_documento_id) in objetivos_a_corregir(usuario)


def _exigir_editable(usuario, objetivo, tipo_documento_id=None):
    if not puede_editar(usuario, objetivo, tipo_documento_id):
        raise ErrorDeNegocio(MENSAJE_BLOQUEADO)


def _historial(usuario, tipo, descripcion, **kwargs):
    from apps.solicitudes import historial

    historial.registrar_en_solicitud_actual(usuario, tipo, descripcion, **kwargs)


def cuota_usada(usuario, sin_tipo=None, sin_foto=False):
    """Bytes de archivos vigentes del aspirante (documentos y foto), RNF-005."""
    perfil = perfil_de(usuario)
    documentos = perfil.documentos.filter(vigente=True)
    if sin_tipo is not None:
        documentos = documentos.exclude(tipo=sin_tipo)
    total = sum(documentos.values_list("tamano", flat=True))
    return total if sin_foto else total + _tamano(usuario.foto)


def verificar_cuota(usuario, tamano_nuevo, sin_tipo=None, sin_foto=False):
    usada = cuota_usada(usuario, sin_tipo=sin_tipo, sin_foto=sin_foto)
    if usada + tamano_nuevo > MAX_TOTAL_MB * 1024 * 1024:
        libre = max(MAX_TOTAL_MB * 1024 * 1024 - usada, 0) / (1024 * 1024)
        raise ErrorDeNegocio(f"Superarías el límite de {MAX_TOTAL_MB} MB por aspirante. Te quedan {libre:.1f} MB libres.")


def validar_foto(usuario, archivo):
    """Comprobaciones de negocio al cambiar la foto de un aspirante (la valida `UsuarioActualSerializer`)."""
    _exigir_editable(usuario, "foto")
    if archivo is not None:
        verificar_cuota(usuario, archivo.size, sin_foto=True)


def foto_cambiada(usuario):
    from apps.solicitudes.models import EventoHistorial

    _historial(usuario, EventoHistorial.Tipo.DATOS, "Cambió la foto de perfil")
    actualizar_perfil_completo(perfil_de(usuario))


# Campo del perfil → elemento que se puede observar.
OBJETIVO_DE_CAMPO = {"centro_trabajo": "centro_trabajo", "indice_declarado": "indice"}
NOMBRE_DE_CAMPO = {"centro_trabajo": "centro de trabajo", "indice_declarado": "índice declarado"}


@transaction.atomic
def actualizar_datos(usuario, datos):
    from apps.solicitudes.models import EventoHistorial

    perfil = PerfilAspirante.objects.select_for_update().get(pk=perfil_de(usuario).pk)
    cambios = {campo: valor for campo, valor in datos.items() if getattr(perfil, campo) != valor}
    for campo in cambios:
        _exigir_editable(usuario, OBJETIVO_DE_CAMPO[campo])
    if not cambios:
        return perfil

    antes = {campo: _texto(getattr(perfil, campo)) for campo in cambios}
    for campo, valor in cambios.items():
        setattr(perfil, campo, valor)
    # Si cambia el índice declarado, la validación anterior deja de valer.
    if "indice_declarado" in cambios and perfil.indice_validado is not None:
        perfil.indice_validado = perfil.indice_validado_por = perfil.indice_validado_at = None
    perfil.save()
    _historial(
        usuario, EventoHistorial.Tipo.DATOS, "Cambió " + ", ".join(NOMBRE_DE_CAMPO[c] for c in cambios),
        antes=antes, despues={campo: _texto(valor) for campo, valor in cambios.items()},
    )
    actualizar_perfil_completo(perfil)
    return perfil


def _texto(valor):
    return None if valor is None else str(valor)


@transaction.atomic
def subir_documento(usuario, tipo, archivo, formato):
    """Sube una versión nueva del documento `tipo`; pasa a ser la vigente."""
    from apps.solicitudes.models import EventoHistorial

    perfil = PerfilAspirante.objects.select_for_update().get(pk=perfil_de(usuario).pk)
    _exigir_editable(usuario, "documento", tipo.pk)
    if not tipo.activo:
        raise ErrorDeNegocio("Ese documento ya no se solicita.")
    verificar_cuota(usuario, archivo.size, sin_tipo=tipo)

    versiones = perfil.documentos.filter(tipo=tipo)
    ultima = versiones.order_by("-version").first()
    versiones.filter(vigente=True).update(vigente=False)
    documento = DocumentoAspirante(
        perfil=perfil,
        tipo=tipo,
        version=ultima.version + 1 if ultima else 1,
        formato=formato,
        tamano=archivo.size,
        nombre_original=(archivo.name or "documento")[:255],
    )
    documento.archivo.save(f"documento.{EXTENSION[formato]}", archivo, save=False)
    documento.save()
    _historial(
        usuario, EventoHistorial.Tipo.DOCUMENTO,
        f"{'Sustituyó' if ultima else 'Subió'} {tipo.nombre}",
        antes={"version": ultima.version, "archivo": ultima.nombre_original} if ultima else None,
        despues={"version": documento.version, "archivo": documento.nombre_original},
    )
    _podar_versiones(perfil, tipo)
    actualizar_perfil_completo(perfil)
    return documento


def _podar_versiones(perfil, tipo):
    """Deja como máximo MAX_VERSIONES por documento: borra las más antiguas y sus archivos."""
    sobrantes = list(perfil.documentos.filter(tipo=tipo).order_by("-version")[MAX_VERSIONES:])
    for documento in sobrantes:
        nombre = documento.archivo.name
        documento.delete()
        transaction.on_commit(lambda nombre=nombre: default_storage.delete(nombre))


def puede_ver_documentos(usuario, aspirante):
    """¿Puede `usuario` ver los documentos y la foto de `aspirante`?

    El propio aspirante, siempre. El personal, si tiene el permiso
    solicitudes.documentos_descargar y además es global o su entidad oferta
    alguna de las carreras de una solicitud confirmada del aspirante.
    """
    if usuario.pk == aspirante.pk:
        return True
    if not usuario.tiene_permiso("solicitudes", DESCARGAR_DOCUMENTOS):
        return False
    if usuario.es_global:
        return True

    from apps.solicitudes.models import Solicitud, SolicitudCarrera

    carreras = SolicitudCarrera.objects.filter(solicitud__aspirante=aspirante).exclude(solicitud__estado=Solicitud.Estado.BORRADOR)
    if usuario.facultad_id:
        return carreras.filter(oferta__facultad_id=usuario.facultad_id).exists()
    if usuario.cum_fum_id:
        return carreras.filter(oferta__cum_fum_id=usuario.cum_fum_id).exists()
    return False


def puede_ver_historial(usuario):
    """Las versiones anteriores solo las consultan los roles globales con el permiso de descarga."""
    return usuario.es_global and usuario.tiene_permiso("solicitudes", DESCARGAR_DOCUMENTOS)
