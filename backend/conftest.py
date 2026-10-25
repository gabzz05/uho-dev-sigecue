import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.roles.models import Rol
from apps.users.models import Usuario


@pytest.fixture(autouse=True)
def _entorno_de_pruebas(settings, tmp_path):
    # Argon2 es lento a propósito; en pruebas basta un hasher rápido.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.PUBLIC_MEDIA_ROOT = tmp_path / "media_publica"
    # El throttle guarda sus contadores en caché: cada prueba empieza de cero.
    cache.clear()


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
def municipio(db):
    from apps.nomencladores.models import Municipio

    return Municipio.objects.get(nombre="Holguín")


@pytest.fixture
def facultad(municipio):
    from apps.nomencladores.models import Facultad

    return Facultad.objects.create(nombre="Facultad de Informática", codigo="FINF", municipio=municipio)


@pytest.fixture
def otra_facultad(municipio):
    from apps.nomencladores.models import Facultad

    return Facultad.objects.create(nombre="Facultad de Ciencias Económicas", codigo="FCE", municipio=municipio)


@pytest.fixture
def cum(db):
    from apps.nomencladores.models import CumFum, Municipio

    return CumFum.objects.create(
        nombre="CUM Calixto García", codigo="CUMCG", tipo="CUM", municipio=Municipio.objects.get(nombre="Calixto García")
    )


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
