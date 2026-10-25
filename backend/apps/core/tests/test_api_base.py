import pytest
from django.urls import path
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIClient

from apps.core.exceptions import ErrorDeNegocio


class _DatosSerializer(serializers.Serializer):
    nombre = serializers.CharField()


@api_view(["POST"])
@permission_classes([AllowAny])
def _validar(request):
    _DatosSerializer(data=request.data).is_valid(raise_exception=True)
    return Response({})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def _privado(request):
    return Response({})


@api_view(["GET"])
@permission_classes([AllowAny])
def _regla(request):
    raise ErrorDeNegocio("La convocatoria está cerrada.")


@api_view(["GET"])
@permission_classes([AllowAny])
def _falla(request):
    raise RuntimeError("boom")


urlpatterns = [
    path("validar/", _validar),
    path("privado/", _privado),
    path("regla/", _regla),
    path("falla/", _falla),
]

pytestmark = pytest.mark.urls(__name__)


@pytest.fixture
def client():
    return APIClient(raise_request_exception=False)


def test_error_de_validacion_incluye_detalles_por_campo(client):
    response = client.post("/validar/", {}, format="json")

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["codigo"] == "invalid"
    assert "nombre" in error["detalles"]


def test_no_autenticado_devuelve_mensaje_en_espanol(client):
    response = client.get("/privado/")

    assert response.status_code in (401, 403)
    assert response.json()["error"]["codigo"] == "not_authenticated"
    assert "iniciar sesión" in response.json()["error"]["mensaje"]


def test_error_de_negocio_usa_su_propio_mensaje(client):
    response = client.get("/regla/")

    assert response.status_code == 400
    assert response.json()["error"] == {
        "codigo": "regla_de_negocio",
        "mensaje": "La convocatoria está cerrada.",
    }


def test_error_inesperado_no_expone_detalles_internos(client):
    response = client.get("/falla/")

    assert response.status_code == 500
    assert response.json()["error"]["codigo"] == "error_interno"
    assert "boom" not in response.content.decode()


def test_ruta_inexistente_devuelve_404_uniforme(client):
    response = client.get("/no-existe/")

    assert response.status_code == 404
