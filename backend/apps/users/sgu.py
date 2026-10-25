"""Adaptador para el Sistema de Gestión de Usuarios de la UHO (auth.uho.edu.cu).

El SGU todavía no está conectado: por defecto `obtener_proveedor()` devuelve
None y los usuarios internos se autentican con su contraseña local.

Para conectarlo se implementa una subclase de `ProveedorSGU` (OAuth 2.0 o
LDAP, según lo que provea el SGU) y se indica su ruta en la variable de
entorno `SGU_PROVEEDOR`. Ver docs/SGU.md.
"""

from dataclasses import dataclass

from django.conf import settings
from django.utils.module_loading import import_string


@dataclass(frozen=True)
class IdentidadSGU:
    username: str
    nombre: str = ""
    apellidos: str = ""
    email: str = ""


class ProveedorSGU:
    """Contrato que debe cumplir la integración con el SGU."""

    def autenticar(self, username: str, password: str) -> IdentidadSGU | None:
        """Devuelve la identidad si las credenciales son válidas en el SGU, o None."""
        raise NotImplementedError


def obtener_proveedor() -> ProveedorSGU | None:
    ruta = getattr(settings, "SGU_PROVEEDOR", "")
    return import_string(ruta)() if ruta else None
