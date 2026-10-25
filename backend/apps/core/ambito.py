"""Ámbito de datos por rol (RG-027, criterio de aceptación 11).

Los roles globales ven todas las entidades. Los locales solo la suya:
su Facultad o su CUM/FUM. Cada módulo aplica `filtrar_por_entidad` a sus
querysets indicando por qué campos se llega a la entidad.
"""


def filtrar_por_entidad(qs, usuario, campo_facultad="facultad", campo_cum_fum="cum_fum"):
    if usuario.es_global:
        return qs
    if usuario.facultad_id:
        return qs.filter(**{campo_facultad: usuario.facultad_id})
    if usuario.cum_fum_id:
        return qs.filter(**{campo_cum_fum: usuario.cum_fum_id})
    # Rol local sin entidad asignada: no ve nada en lugar de verlo todo.
    return qs.none()


def es_de_su_entidad(usuario, facultad, cum_fum):
    """¿La entidad indicada (una de las dos) está dentro del ámbito del usuario?"""
    if usuario.es_global:
        return True
    if facultad is not None:
        return facultad.pk == usuario.facultad_id
    if cum_fum is not None:
        return cum_fum.pk == usuario.cum_fum_id
    return False
