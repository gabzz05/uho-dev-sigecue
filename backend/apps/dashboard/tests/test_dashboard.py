from datetime import timedelta

import pytest
from django.utils import timezone

from apps.interes.models import ConvocatoriaInteres, ExpresionInteres
from apps.otorgamiento.tests.test_otorgamiento import escenario, otorgamiento, usuarios  # noqa: F401 (fixtures)

pytestmark = pytest.mark.django_db

DASHBOARD = "/api/v1/admin/dashboard/"
ESTADISTICAS = "/api/v1/admin/interes/expresiones/estadisticas/"
HOY = timezone.localdate()


@pytest.fixture
def interes(ofertas):
    convocatoria = ConvocatoriaInteres.objects.create(
        anio_academico="2026-2027", fecha_inicio=HOY - timedelta(days=5), fecha_cierre=HOY + timedelta(days=2), estado="abierta"
    )
    for i, oferta in enumerate([ofertas["informatica_facultad"], ofertas["informatica_facultad"], ofertas["derecho_cum"]]):
        ExpresionInteres.objects.create(
            convocatoria=convocatoria, oferta=oferta, nombre=f"Persona {i}", ci=f"9001011230{i}", celular="55111111", email=f"p{i}@nauta.cu"
        )
    return convocatoria


class TestEstadisticasInteres:
    def test_totales_por_carrera_entidad_y_municipio(self, api_como, crear_usuario, interes):
        datos = api_como(crear_usuario("jefe", rol="jefe_ci")).get(ESTADISTICAS, {"convocatoria": interes.pk}).json()

        assert datos["total"] == 3
        assert datos["por_carrera"][0] == {"carrera": "Ingeniería Informática", "total": 2}
        assert datos["por_entidad"] == [{"entidad": "Facultad de Informática", "total": 2}, {"entidad": "CUM Calixto García", "total": 1}]
        municipios = {m["nombre"]: m["total"] for m in datos["por_municipio"]}
        assert len(municipios) == 14
        # Por el municipio de la entidad que oferta la carrera.
        assert (municipios["Holguín"], municipios["Calixto García"], municipios["Banes"]) == (2, 1, 0)
        assert datos["evolucion"] == [{"dia": str(HOY), "total": 3}]

    def test_un_rol_local_solo_su_entidad(self, api_como, crear_usuario, cum, interes):
        local = crear_usuario("sec_cum", rol="secretario_cum", cum_fum=cum)

        datos = api_como(local).get(ESTADISTICAS).json()

        assert datos["total"] == 1
        assert [e["entidad"] for e in datos["por_entidad"]] == ["CUM Calixto García"]


class TestDashboard:
    def test_sin_datos(self, api_como, superadmin):
        datos = api_como(superadmin).get(DASHBOARD).json()

        assert (datos["secciones"], datos["alertas"]) == ({}, [])

    def test_aspirante_no_entra(self, api_como, aspirante):
        assert api_como(aspirante).get(DASHBOARD).status_code == 403

    def test_alerta_de_convocatoria_proxima_a_cerrar(self, api_como, crear_usuario, interes):
        datos = api_como(crear_usuario("jefe", rol="jefe_ci")).get(DASHBOARD).json()

        assert datos["secciones"]["interes"]["expresiones"] == 3
        assert any("cierra en 2 día(s)" in a["texto"] for a in datos["alertas"])

    def test_otorgamiento_pendiente_para_quien_debe_aprobar(self, api_como, usuarios, otorgamiento):  # noqa: F811
        jefe = api_como(usuarios["jefe"]).get(DASHBOARD).json()
        vicerrector = api_como(usuarios["vicerrector"]).get(DASHBOARD).json()

        assert jefe["secciones"]["otorgamiento"]["estado"] == "Revisión del Jefe CI"
        assert any(a["nivel"] == "atencion" and "pendiente de tu aprobación" in a["texto"] for a in jefe["alertas"])
        assert not any("pendiente de tu aprobación" in a["texto"] for a in vicerrector["alertas"])

    def test_un_rol_local_ve_su_ambito_y_no_el_provisional(self, api_como, usuarios, otorgamiento):  # noqa: F811
        datos = api_como(usuarios["sec_cum"]).get(DASHBOARD).json()

        # Luis (Informática CUM) y Eva (Derecho CUM) tienen opciones en el CUM; Ana también (Derecho CUM, 2.ª).
        assert datos["secciones"]["solicitudes"]["total"] == 3
        assert datos["secciones"]["otorgamiento"] == {"convocatoria": "1.ª 2026-2027", "estado": "En elaboración", "otorgadas": None}

    def test_falta_generar_el_otorgamiento(self, api_como, usuarios, escenario):  # noqa: F811
        datos = api_como(usuarios["secretaria"]).get(DASHBOARD).json()

        assert any("falta generar el otorgamiento" in a["texto"] for a in datos["alertas"])
