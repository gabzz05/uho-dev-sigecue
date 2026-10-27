"""Historial del expediente del aspirante (RF-054).

Se registra al guardar (no en cada arrastre): selección de carreras,
confirmación, documentos, datos del perfil, índice y observaciones.
"""

from .models import EventoHistorial

T = EventoHistorial.Tipo


def instantanea_seleccion(solicitud):
    """Selección actual como lista serializable, con la entidad de cada opción para filtrarla por ámbito."""
    return [
        {
            "prioridad": c.prioridad,
            "carrera": c.oferta.carrera.nombre,
            "entidad": str(c.oferta.entidad),
            "facultad_id": c.oferta.facultad_id,
            "cum_fum_id": c.oferta.cum_fum_id,
        }
        for c in solicitud.carreras.select_related("oferta__carrera", "oferta__facultad", "oferta__cum_fum").order_by("prioridad")
    ]


def registrar(aspirante, tipo, descripcion, *, usuario=None, solicitud=None, antes=None, despues=None):
    return EventoHistorial.objects.create(
        aspirante=aspirante,
        solicitud=solicitud,
        usuario=usuario,
        tipo=tipo,
        descripcion=descripcion[:255],
        antes=antes,
        despues=despues,
    )


def registrar_en_solicitud_actual(aspirante, tipo, descripcion, **kwargs):
    """Para cambios del perfil (documentos, datos): se asocian a la solicitud vigente, si hay."""
    from .services import solicitud_actual

    return registrar(aspirante, tipo, descripcion, usuario=aspirante, solicitud=solicitud_actual(aspirante), **kwargs)


def visible_para(evento, usuario):
    """Copia del evento para mostrar a `usuario`: un rol local solo ve las opciones de su entidad (minimización)."""
    datos = {"antes": evento.antes, "despues": evento.despues}
    if evento.tipo == T.SELECCION and not usuario.es_global and not usuario.es_aspirante:
        for clave in ("antes", "despues"):
            if datos[clave] is not None:
                datos[clave] = [o for o in datos[clave] if _de_su_entidad(o, usuario)]
    return datos


def _de_su_entidad(opcion, usuario):
    if usuario.facultad_id:
        return opcion.get("facultad_id") == usuario.facultad_id
    if usuario.cum_fum_id:
        return opcion.get("cum_fum_id") == usuario.cum_fum_id
    return False
