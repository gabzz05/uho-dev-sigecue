from rest_framework.permissions import BasePermission


class EsAspirante(BasePermission):
    """Portal del aspirante: solo cuentas de aspirante (cada una ve únicamente lo suyo)."""

    message = "Esta sección es solo para aspirantes."

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.es_aspirante)
