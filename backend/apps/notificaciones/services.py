"""Notificaciones in-app + correo (RF-073 a RF-076).

- `notificar`: notificaciones automáticas a partir de una plantilla de correo.
  El texto in-app y el del correo son el mismo.
- `enviar_masivo`: mensaje redactado por un administrador a un grupo.
"""

from django.db import transaction

from apps.configuracion import plantillas
from apps.configuracion.services import texto_plantilla
from apps.core.ambito import filtrar_por_entidad
from apps.core.exceptions import ErrorDeNegocio
from apps.nomencladores.models import CumFum, Facultad
from apps.roles.models import Rol
from apps.users.models import Usuario

from .models import EnvioMasivo, Notificacion

VARIABLES_MASIVAS = {"nombre": "Nombre del destinatario"}


def _contexto_de(usuario, contexto):
    base = {"nombre": usuario.first_name or usuario.username}
    extra = contexto(usuario) if callable(contexto) else (contexto or {})
    return base | extra


def _crear(usuarios, tipo, asunto, cuerpo, contexto, por_correo, envio=None):
    notificaciones = Notificacion.objects.bulk_create(
        [
            Notificacion(
                usuario=usuario,
                tipo=tipo,
                asunto=plantillas.renderizar(asunto, ctx)[:200],
                cuerpo=plantillas.renderizar(cuerpo, ctx),
                envio=envio,
            )
            for usuario in usuarios
            for ctx in [_contexto_de(usuario, contexto)]
        ]
    )
    if por_correo and notificaciones:
        from .tasks import enviar_correos

        ids = [n.pk for n in notificaciones]
        transaction.on_commit(lambda: enviar_correos.delay(ids))
    return notificaciones


@transaction.atomic
def notificar(usuarios, codigo, contexto=None, por_correo=True):
    """Notifica a `usuarios` con la plantilla `codigo` (in-app y, por defecto, correo).

    `contexto` es un dict con las variables o una función `usuario -> dict` para
    variables distintas por destinatario. `nombre` se rellena solo.
    """
    asunto, cuerpo = texto_plantilla(codigo)
    return _crear(list(usuarios), codigo, asunto, cuerpo, contexto, por_correo)


# --- Envíos masivos (RF-076) -------------------------------------------------

TIPOS_GRUPO = ("rol", "entidad", "aspirantes")


def resolver_grupo(grupo, actor):
    """Usuarios activos de un grupo, dentro del ámbito de quien envía.

    Devuelve `(queryset, descripción, facultad, cum_fum)`.
    """
    tipo = grupo.get("tipo")
    activos = Usuario.objects.filter(is_active=True).select_related("rol")

    if tipo == "aspirantes":
        if not actor.es_global:
            raise ErrorDeNegocio("Solo los roles globales pueden notificar a todos los aspirantes.")
        qs = activos.filter(rol__codigo=Rol.ASPIRANTE, email_verificado=True)
        return qs, "Todos los aspirantes", None, None

    if tipo == "rol":
        rol = Rol.objects.filter(codigo=grupo.get("rol"), activo=True).exclude(codigo=Rol.ASPIRANTE).first()
        if rol is None:
            raise ErrorDeNegocio("Selecciona un rol válido.")
        qs = filtrar_por_entidad(activos.filter(rol=rol), actor)
        entidad = "" if actor.es_global else f" de {actor.entidad}"
        return qs, f"Rol: {rol.nombre}{entidad}", actor.facultad, actor.cum_fum

    if tipo == "entidad":
        if actor.es_global:
            facultad = Facultad.objects.filter(pk=grupo.get("facultad")).first() if grupo.get("facultad") else None
            cum_fum = CumFum.objects.filter(pk=grupo.get("cum_fum")).first() if grupo.get("cum_fum") else None
            if (facultad is None) == (cum_fum is None):
                raise ErrorDeNegocio("Selecciona una Facultad o un CUM/FUM.")
        else:
            facultad, cum_fum = actor.facultad, actor.cum_fum
            if facultad is None and cum_fum is None:
                raise ErrorDeNegocio("Tu usuario no tiene una entidad asignada.")
        qs = activos.filter(facultad=facultad) if facultad else activos.filter(cum_fum=cum_fum)
        return qs, f"Usuarios de {facultad or cum_fum}", facultad, cum_fum

    raise ErrorDeNegocio("Tipo de grupo desconocido.")


@transaction.atomic
def enviar_masivo(actor, grupo, asunto, cuerpo, por_correo=False):
    if desconocidas := plantillas.variables_desconocidas(asunto + cuerpo, VARIABLES_MASIVAS):
        raise ErrorDeNegocio(f"Variables no disponibles: {', '.join(desconocidas)}. Solo se admite {{{{ nombre }}}}.")
    usuarios, descripcion, facultad, cum_fum = resolver_grupo(grupo, actor)
    usuarios = list(usuarios)
    if not usuarios:
        raise ErrorDeNegocio("El grupo seleccionado no tiene destinatarios.")

    envio = EnvioMasivo.objects.create(
        enviado_por=actor, grupo=grupo, grupo_descripcion=descripcion[:255], asunto=asunto, cuerpo=cuerpo,
        por_correo=por_correo, destinatarios=len(usuarios), facultad=facultad, cum_fum=cum_fum,
    )
    _crear(usuarios, Notificacion.MASIVA, asunto, cuerpo, None, por_correo, envio=envio)
    return envio
