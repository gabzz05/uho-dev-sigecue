from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.settings import api_settings
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.otorgamiento import services
from apps.otorgamiento.models import Otorgamiento
from apps.otorgamiento.publico import enmascarar_ci

from .test_otorgamiento import escenario, otorgamiento, usuarios  # noqa: F401 (fixtures)

pytestmark = pytest.mark.django_db

LISTADO = "/api/v1/publico/resultados/"
CONSULTA = "/api/v1/publico/resultados/consulta/"
SIN_RESULTADO = "No existe un resultado publicado para los datos introducidos."


@pytest.fixture
def publicado(usuarios, otorgamiento):  # noqa: F811
    services.aprobar(usuarios["jefe"], otorgamiento)
    return services.publicar(usuarios["vicerrector"], otorgamiento, segunda_convocatoria=True)


def test_enmascarar_ci():
    assert enmascarar_ci("98042512345") == "*******2345"


class TestListado:
    def test_sin_publicar_no_hay_nada(self, api, otorgamiento):  # noqa: F811
        assert api.get(LISTADO).json()["count"] == 0

    def test_solo_otorgados_con_datos_minimos(self, api, publicado):
        filas = api.get(LISTADO).json()["results"]

        assert len(filas) == 3  # Pepe (no elegible) no aparece
        assert set(filas[0]) == {"nombre", "ci", "carrera", "entidad", "convocatoria"}
        assert {f["ci"] for f in filas} == {"*******2341", "*******2342", "*******2343"}
        assert filas[0]["convocatoria"] == "1.ª convocatoria 2026-2027"

    def test_orden_carrera_entidad_y_apellidos(self, api, publicado):
        filas = api.get(LISTADO).json()["results"]

        assert [(f["carrera"], f["entidad"]) for f in filas] == sorted((f["carrera"], f["entidad"]) for f in filas)

    def test_filtros(self, api, publicado):
        filtros = api.get(f"{LISTADO}filtros/").json()

        assert filtros["convocatorias"] == [{"id": publicado.pk, "nombre": "1.ª convocatoria 2026-2027"}]
        assert "Derecho" in filtros["carreras"]
        assert api.get(LISTADO, {"carrera": "Derecho"}).json()["count"] == 1
        assert api.get(LISTADO, {"entidad": "CUM Calixto García"}).json()["count"] == 2

    def test_deja_de_verse_al_cerrar_la_prematricula(self, api, publicado):
        Otorgamiento.objects.filter(pk=publicado.pk).update(publico_hasta=timezone.localdate() - timedelta(days=1))

        assert api.get(LISTADO).json()["count"] == 0

    def test_no_hay_descarga_publica(self, publicado):
        anonimo = APIClient()

        assert anonimo.get(f"/api/v1/admin/otorgamiento/{publicado.pk}/exportar-pdf/").status_code == 401
        assert anonimo.get(f"/api/v1/admin/otorgamiento/{publicado.pk}/exportar-excel/").status_code == 401


class TestConsulta:
    def test_otorgado(self, api, publicado):
        response = api.post(CONSULTA, {"ci": "90010112341"}, format="json")

        assert response.status_code == 200
        assert response.json() == {
            "resultados": [
                {"convocatoria": "1.ª convocatoria 2026-2027", "resultado": "Otorgado", "carrera": "Ingeniería Informática", "entidad": "Facultad de Informática"}
            ]
        }

    def test_no_seleccionado(self, api, publicado):
        resultado = api.post(CONSULTA, {"ci": "90010112344"}, format="json").json()["resultados"][0]

        assert resultado == {"convocatoria": "1.ª convocatoria 2026-2027", "resultado": "No seleccionado", "carrera": None, "entidad": None}

    def test_mismo_mensaje_exista_o_no_el_ci(self, api, otorgamiento):  # noqa: F811
        # Sin publicar: el CI existe pero no hay resultado publicado.
        existente = api.post(CONSULTA, {"ci": "90010112341"}, format="json")
        inexistente = api.post(CONSULTA, {"ci": "11111111111"}, format="json")

        assert existente.status_code == inexistente.status_code == 400
        assert existente.json()["error"]["mensaje"] == inexistente.json()["error"]["mensaje"] == SIN_RESULTADO

    def test_ci_con_formato_invalido(self, api):
        assert api.post(CONSULTA, {"ci": "123"}, format="json").status_code == 400

    def test_limite_por_ip(self, api, settings):
        settings.REST_FRAMEWORK = settings.REST_FRAMEWORK | {
            "DEFAULT_THROTTLE_RATES": {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], "resultados": "2/hour"}
        }
        ScopedRateThrottle.THROTTLE_RATES = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        try:
            codigos = [api.post(CONSULTA, {"ci": "11111111111"}, format="json").status_code for _ in range(3)]
        finally:
            ScopedRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES

        assert codigos == [400, 400, 429]
