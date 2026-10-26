import pytest

from apps.aspirantes import services
from apps.aspirantes.models import DocumentoAspirante, TipoDocumento
from apps.auditoria.models import LogAuditoria
from apps.nomencladores.models import Area
from apps.solicitudes.models import Solicitud, SolicitudCarrera

from .fixtures import pdf

pytestmark = pytest.mark.django_db


def url_archivo(documento):
    return f"/api/v1/documentos/{documento.pk}/archivo/"


@pytest.fixture
def certificacion(perfil_listo):
    return DocumentoAspirante.objects.get(tipo__nombre="Certificación de estudios", vigente=True)


@pytest.fixture
def solicitud_en(aspirante, convocatoria):
    """Solicitud del aspirante con una carrera en la oferta indicada."""

    def _crear(oferta, estado=Solicitud.Estado.PENDIENTE):
        solicitud = Solicitud.objects.create(aspirante=aspirante, convocatoria=convocatoria, estado=estado)
        SolicitudCarrera.objects.create(solicitud=solicitud, oferta=oferta, prioridad=1)
        return solicitud

    return _crear


@pytest.fixture
def secretario(crear_usuario, facultad):
    return crear_usuario("sec_fac", rol="secretario_facultad", facultad=facultad)


class TestDescarga:
    def test_el_aspirante_descarga_el_suyo_y_se_audita(self, api_como, aspirante, certificacion):
        response = api_como(aspirante).get(url_archivo(certificacion))

        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert b"".join(response.streaming_content).startswith(b"%PDF-")
        log = LogAuditoria.objects.get(accion="descargar documento")
        assert log.detalle["motivo"] == "consulta_documentacion"
        assert log.detalle["archivo"] == "certificacion.pdf"
        assert log.ip is not None

    def test_otro_aspirante_no_lo_ve(self, api_como, crear_aspirante, certificacion):
        otro = crear_aspirante("asp_otro", ci="99010112345", email="otro@nauta.cu")

        assert api_como(otro).get(url_archivo(certificacion)).status_code == 404

    def test_secretario_de_una_entidad_elegida(self, api_como, secretario, certificacion, solicitud_en, ofertas):
        solicitud_en(ofertas["informatica_facultad"])

        response = api_como(secretario).get(url_archivo(certificacion))

        assert response.status_code == 200
        assert LogAuditoria.objects.get(accion="descargar documento").detalle["motivo"] == "revision_solicitud"

    def test_secretario_de_otra_entidad_no(self, api_como, crear_usuario, otra_facultad, certificacion, solicitud_en, ofertas):
        solicitud_en(ofertas["informatica_facultad"])
        ajeno = crear_usuario("sec_otra", rol="secretario_facultad", facultad=otra_facultad)

        assert api_como(ajeno).get(url_archivo(certificacion)).status_code == 404

    def test_un_borrador_no_da_acceso_a_la_entidad(self, api_como, secretario, certificacion, solicitud_en, ofertas):
        solicitud_en(ofertas["informatica_facultad"], estado=Solicitud.Estado.BORRADOR)

        assert api_como(secretario).get(url_archivo(certificacion)).status_code == 404

    def test_director_de_cum_elegido(self, api_como, crear_usuario, cum, certificacion, solicitud_en, ofertas):
        solicitud_en(ofertas["informatica_cum"])
        director = crear_usuario("dir_cum", rol="director_cum", cum_fum=cum)

        assert api_como(director).get(url_archivo(certificacion)).status_code == 200

    @pytest.mark.parametrize("rol", ["admin_facultad", "vicedecano", "jefe_area_facultad"])
    def test_otros_roles_de_la_entidad_no(self, api_como, crear_usuario, facultad, certificacion, solicitud_en, ofertas, rol):
        solicitud_en(ofertas["informatica_facultad"])
        extra = {"area": Area.objects.create(nombre="Software", facultad=facultad)} if rol == "jefe_area_facultad" else {}
        usuario = crear_usuario("local", rol=rol, facultad=facultad, **extra)

        assert api_como(usuario).get(url_archivo(certificacion)).status_code == 404

    def test_un_rol_global_con_el_permiso(self, api_como, crear_usuario, certificacion):
        assert api_como(crear_usuario("jefe", rol="jefe_ci")).get(url_archivo(certificacion)).status_code == 200

    def test_sin_sesion(self, api, certificacion):
        assert api.get(url_archivo(certificacion)).status_code == 401


class TestHistorial:
    @pytest.fixture
    def anterior(self, aspirante, certificacion):
        services.subir_documento(aspirante, certificacion.tipo, pdf("nueva.pdf"), "PDF")
        certificacion.refresh_from_db()
        return certificacion

    def test_la_entidad_solo_ve_la_vigente(self, api_como, secretario, anterior, solicitud_en, ofertas, aspirante):
        solicitud_en(ofertas["informatica_facultad"])
        client = api_como(secretario)

        assert client.get(url_archivo(anterior)).status_code == 404
        listado = client.get(f"/api/v1/admin/aspirantes/{aspirante.pk}/documentos/").json()
        assert {(d["tipo_nombre"], d["version"]) for d in listado if d["tipo_nombre"] == "Certificación de estudios"} == {("Certificación de estudios", 2)}

    def test_el_aspirante_tampoco_ve_las_anteriores(self, api_como, aspirante, anterior):
        assert api_como(aspirante).get(url_archivo(anterior)).status_code == 404

    def test_un_rol_global_ve_todo_el_historial(self, api_como, crear_usuario, anterior, aspirante):
        client = api_como(crear_usuario("jefe", rol="jefe_ci"))

        assert client.get(url_archivo(anterior)).status_code == 200
        listado = client.get(f"/api/v1/admin/aspirantes/{aspirante.pk}/documentos/").json()
        assert sorted(d["version"] for d in listado if d["tipo_nombre"] == "Certificación de estudios") == [1, 2]


class TestFotoDelAspirante:
    def test_la_ve_quien_puede_ver_sus_documentos(self, api_como, secretario, perfil_listo, aspirante, solicitud_en, ofertas):
        solicitud_en(ofertas["informatica_facultad"])

        response = api_como(secretario).get(f"/api/v1/admin/aspirantes/{aspirante.pk}/foto/")

        assert response.status_code == 200
        assert LogAuditoria.objects.filter(accion="ver foto de aspirante").exists()

    def test_sin_relacion_no(self, api_como, secretario, perfil_listo, aspirante):
        assert api_como(secretario).get(f"/api/v1/admin/aspirantes/{aspirante.pk}/foto/").status_code == 404


class TestTiposDocumento:
    URL = "/api/v1/admin/tipos-documento/"

    def test_el_superadmin_los_gestiona(self, api_como, superadmin):
        client = api_como(superadmin)

        creado = client.post(self.URL, {"nombre": "Aval laboral", "obligatorio": False, "orden": 4}, format="json")
        assert creado.status_code == 201
        assert client.patch(f"{self.URL}{creado.json()['id']}/", {"activo": False}, format="json").status_code == 200
        assert client.delete(f"{self.URL}{creado.json()['id']}/").status_code == 204

    def test_otro_rol_no_los_modifica(self, api_como, crear_usuario):
        response = api_como(crear_usuario("jefe", rol="jefe_ci")).post(self.URL, {"nombre": "X"}, format="json")

        assert response.status_code == 403

    def test_no_se_borra_si_ya_se_subio(self, api_como, superadmin, certificacion):
        response = api_como(superadmin).delete(f"{self.URL}{certificacion.tipo.pk}/")

        assert response.status_code == 400
        assert TipoDocumento.objects.filter(pk=certificacion.tipo.pk).exists()
