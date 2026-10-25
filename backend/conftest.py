import pytest
from rest_framework.test import APIClient

from apps.roles.models import Rol
from apps.users.models import Usuario


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def crear_usuario(db):
    """Crea un usuario interno con el rol indicado por su código."""

    def _crear(username="usuario", rol=None, password="Clave-Segura-123", **extra):
        if rol is not None and not isinstance(rol, Rol):
            rol = Rol.objects.get(codigo=rol)
        return Usuario.objects.create_user(username=username, password=password, rol=rol, **extra)

    return _crear


@pytest.fixture
def superadmin(crear_usuario):
    return crear_usuario("superadmin", rol="superadmin")


@pytest.fixture
def api_como(api):
    """Devuelve el cliente autenticado como el usuario dado."""

    def _como(usuario):
        api.force_authenticate(usuario)
        return api

    return _como
