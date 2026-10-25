from rest_framework.test import APIClient


def test_swagger_disponible_en_api_docs():
    assert APIClient().get("/api/docs/").status_code == 200


def test_esquema_openapi_incluye_rutas_v1():
    response = APIClient().get("/api/schema/", HTTP_ACCEPT="application/json")

    assert response.status_code == 200
    assert "/api/v1/health/" in response.json()["paths"]
