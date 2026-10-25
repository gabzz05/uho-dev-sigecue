import pytest

from apps.roles.models import Rol
from apps.users.models import Usuario

PASSWORD = "Clave-Segura-123"


@pytest.fixture
def aspirante(db):
    """Aspirante con la cuenta ya activada."""
    usuario = Usuario(
        username="asp_maria",
        first_name="María",
        last_name="González Pérez",
        email="maria@nauta.cu",
        ci="98042512345",
        celular="55123456",
        rol=Rol.objects.get(codigo=Rol.ASPIRANTE),
        email_verificado=True,
    )
    usuario.set_password(PASSWORD)
    usuario.save()
    return usuario


@pytest.fixture
def datos_registro():
    return {
        "nombre": "Carlos",
        "apellidos": "Martínez López",
        "ci": "96071834521",
        "email": "carlos@nauta.cu",
        "celular": "55987654",
        "password": PASSWORD,
        "acepta_privacidad": True,
    }
