from rest_framework.permissions import BasePermission

from .catalogo import CREAR, ELIMINAR, EDITAR, VER

ACCION_POR_DEFECTO = {
    "list": VER,
    "retrieve": VER,
    "create": CREAR,
    "update": EDITAR,
    "partial_update": EDITAR,
    "destroy": ELIMINAR,
}


class PermisoModulo(BasePermission):
    """Autoriza según los permisos del rol del usuario (RE-006).

    La vista declara `modulo = "usuarios"`. La acción del ViewSet se traduce a
    una acción del catálogo con `ACCION_POR_DEFECTO`; las acciones propias
    (`@action`) deben declararse en `acciones_permiso = {"bloquear": EDITAR}`.
    Una acción sin traducción se deniega.
    """

    def has_permission(self, request, view):
        usuario = request.user
        if not usuario or not usuario.is_authenticated:
            return False

        action_map = getattr(view, "action_map", None)
        if action_map is not None and request.method.lower() not in action_map:
            return True  # Método no disponible en esta ruta: DRF responde 405.

        accion_vista = getattr(view, "action", None) or request.method.lower()
        mapa = ACCION_POR_DEFECTO | getattr(view, "acciones_permiso", {})
        accion = mapa.get(accion_vista)
        if accion is None:
            return False
        return usuario.tiene_permiso(view.modulo, accion)
