import pytest
from django.core import mail

from apps.aspirantes.models import PerfilAspirante
from apps.aspirantes.tests.fixtures import cerrar
from apps.configuracion.models import ConfiguracionSistema
from apps.notificaciones.models import Notificacion
from apps.oferta.models import OfertaCarrera
from apps.solicitudes.models import Solicitud

pytestmark = pytest.mark.django_db

URL = "/api/v1/solicitudes/"


@pytest.fixture
def client(api_como, aspirante):
    return api_como(aspirante)


@pytest.fixture
def borrador(client, perfil_listo, convocatoria):
    return client.post(URL).json()


def guardar(client, solicitud, *ofertas):
    return client.put(f"{URL}{solicitud['id']}/carreras/", {"ofertas": [o.pk for o in ofertas]}, format="json")


class TestBorrador:
    def test_solo_para_aspirantes(self, api_como, crear_usuario):
        assert api_como(crear_usuario("sec", rol="secretario_facultad")).get(URL).status_code == 403

    def test_sin_convocatoria_abierta_no_se_crea(self, client):
        response = client.post(URL)

        assert response.status_code == 400
        assert "No hay una convocatoria" in response.json()["error"]["mensaje"]

    def test_crea_el_borrador_una_sola_vez(self, client, convocatoria):
        primera = client.post(URL)
        segunda = client.post(URL)

        assert primera.status_code == 201
        assert primera.json()["id"] == segunda.json()["id"]
        assert (primera.json()["estado"], primera.json()["editable"], primera.json()["max_carreras"]) == ("borrador", True, 5)
        assert primera.json()["confirmada_at"] is None

    def test_ofertas_elegibles_de_la_convocatoria(self, client, convocatoria, ofertas):
        datos = client.get(f"{URL}ofertas/").json()

        assert {o["id"] for o in datos} == {ofertas[k].pk for k in ("informatica_facultad", "informatica_cum", "informatica_banes", "derecho_cum")}
        cum = next(o for o in datos if o["id"] == ofertas["informatica_cum"].pk)
        assert (cum["tipo_entidad"], cum["entidad_nombre"], cum["municipio"], cum["plazas"]) == ("cum_fum", "CUM Calixto García", "Calixto García", 10)

    def test_sin_convocatoria_no_hay_ofertas(self, client, ofertas):
        assert client.get(f"{URL}ofertas/").json() == []

    def test_cada_aspirante_ve_solo_las_suyas(self, api_como, crear_aspirante, borrador):
        otro = api_como(crear_aspirante("asp_otro", ci="99010112345", email="otro@nauta.cu"))

        assert otro.get(URL).json() == []
        assert otro.get(f"{URL}{borrador['id']}/").status_code == 404


class TestSeleccion:
    def test_exige_el_perfil_completo(self, client, convocatoria, ofertas):
        solicitud = client.post(URL).json()

        response = guardar(client, solicitud, ofertas["derecho_cum"])

        assert response.status_code == 400
        assert "Completa tu perfil" in response.json()["error"]["mensaje"]

    def test_guarda_en_orden_de_prioridad(self, client, borrador, ofertas, aspirante):
        response = guardar(client, borrador, ofertas["derecho_cum"], ofertas["informatica_facultad"])

        assert response.status_code == 200
        assert [(c["prioridad"], c["oferta"]["id"]) for c in response.json()["carreras"]] == [
            (1, ofertas["derecho_cum"].pk), (2, ofertas["informatica_facultad"].pk),
        ]
        assert response.json()["modificada_at"] is not None
        assert PerfilAspirante.objects.get(usuario=aspirante).perfil_completo is True

    def test_reordenar_reemplaza_la_seleccion(self, client, borrador, ofertas):
        guardar(client, borrador, ofertas["derecho_cum"], ofertas["informatica_facultad"])

        response = guardar(client, borrador, ofertas["informatica_facultad"], ofertas["derecho_cum"])

        assert [c["oferta"]["id"] for c in response.json()["carreras"]] == [ofertas["informatica_facultad"].pk, ofertas["derecho_cum"].pk]

    def test_maximo_segun_el_parametro(self, client, borrador, ofertas):
        ConfiguracionSistema.objects.update(max_carreras_aspirante=1)

        response = guardar(client, borrador, ofertas["derecho_cum"], ofertas["informatica_facultad"])

        assert response.status_code == 400
        assert "como máximo 1" in response.json()["error"]["mensaje"]

    def test_la_misma_carrera_en_facultad_y_cum_si(self, client, borrador, ofertas):
        assert guardar(client, borrador, ofertas["informatica_facultad"], ofertas["informatica_cum"]).status_code == 200

    def test_la_misma_carrera_en_dos_cum_no(self, client, borrador, ofertas):
        response = guardar(client, borrador, ofertas["informatica_cum"], ofertas["informatica_banes"])

        assert response.status_code == 400
        assert "dos CUM/FUM" in response.json()["error"]["mensaje"]

    def test_la_misma_oferta_dos_veces_no(self, client, borrador, ofertas):
        assert guardar(client, borrador, ofertas["derecho_cum"], ofertas["derecho_cum"]).status_code == 400

    def test_una_oferta_sin_plazas_no(self, client, borrador, ofertas):
        assert guardar(client, borrador, ofertas["sin_plazas"]).status_code == 400

    def test_una_oferta_de_otro_anio_no(self, client, borrador, carreras, facultad):
        otra = OfertaCarrera.objects.create(carrera=carreras["derecho"], facultad=facultad, anio_academico="2027-2028", plazas_plan=4)

        assert guardar(client, borrador, otra).status_code == 400

    def test_una_entidad_fuera_de_la_convocatoria_no(self, client, borrador, convocatoria, ofertas, facultad):
        convocatoria.facultades.set([facultad])

        assert guardar(client, borrador, ofertas["derecho_cum"]).status_code == 400
        assert guardar(client, borrador, ofertas["informatica_facultad"]).status_code == 200

    def test_una_oferta_inexistente(self, client, borrador):
        response = client.put(f"{URL}{borrador['id']}/carreras/", {"ofertas": [999999]}, format="json")

        assert response.status_code == 400

    def test_con_la_convocatoria_cerrada_queda_congelada(self, client, borrador, ofertas, convocatoria):
        guardar(client, borrador, ofertas["derecho_cum"])
        cerrar(convocatoria)

        response = guardar(client, borrador, ofertas["informatica_facultad"])

        assert response.status_code == 400
        assert client.get(f"{URL}{borrador['id']}/").json()["editable"] is False


class TestConfirmar:
    @pytest.fixture(autouse=True)
    def _on_commit(self, django_capture_on_commit_callbacks):
        self.capturar = django_capture_on_commit_callbacks

    def confirmar(self, client, solicitud):
        with self.capturar(execute=True):
            return client.post(f"{URL}{solicitud['id']}/confirmar/")

    def test_confirma_y_avisa_una_vez(self, client, borrador, ofertas, aspirante):
        guardar(client, borrador, ofertas["informatica_facultad"], ofertas["derecho_cum"])

        response = self.confirmar(client, borrador)

        assert response.status_code == 200
        assert (response.json()["estado"], response.json()["estado_nombre"]) == ("pendiente", "Pendiente")
        assert response.json()["confirmada_at"] is not None
        notificacion = Notificacion.objects.get(usuario=aspirante)
        assert notificacion.tipo == "solicitud_confirmada"
        assert "1. Ingeniería Informática — Facultad de Informática" in notificacion.cuerpo
        assert "2. Derecho — CUM Calixto García" in notificacion.cuerpo
        assert len(mail.outbox) == 1 and mail.outbox[0].to == ["maria@nauta.cu"]

    def test_los_cambios_posteriores_no_notifican(self, client, borrador, ofertas):
        guardar(client, borrador, ofertas["informatica_facultad"])
        confirmada = self.confirmar(client, borrador).json()

        response = guardar(client, borrador, ofertas["derecho_cum"], ofertas["informatica_facultad"])

        assert response.status_code == 200
        assert response.json()["estado"] == "pendiente"
        assert response.json()["confirmada_at"] == confirmada["confirmada_at"]
        assert response.json()["modificada_at"] > confirmada["modificada_at"]
        assert Notificacion.objects.count() == 1 and len(mail.outbox) == 1

    def test_no_se_confirma_dos_veces(self, client, borrador, ofertas):
        guardar(client, borrador, ofertas["informatica_facultad"])
        self.confirmar(client, borrador)

        assert self.confirmar(client, borrador).status_code == 400

    def test_sin_carreras_no(self, client, borrador):
        response = self.confirmar(client, borrador)

        assert response.status_code == 400
        assert "al menos una carrera" in response.json()["error"]["mensaje"]

    def test_confirmada_no_se_vacia(self, client, borrador, ofertas):
        guardar(client, borrador, ofertas["informatica_facultad"])
        self.confirmar(client, borrador)

        assert guardar(client, borrador).status_code == 400

    def test_dice_que_falta_del_perfil(self, client, borrador, ofertas, aspirante):
        guardar(client, borrador, ofertas["informatica_facultad"])
        perfil = PerfilAspirante.objects.get(usuario=aspirante)
        perfil.centro_trabajo = ""
        perfil.save()

        response = self.confirmar(client, borrador)

        assert response.status_code == 400
        assert "centro de trabajo" in response.json()["error"]["mensaje"]
        assert Solicitud.objects.get(pk=borrador["id"]).estado == Solicitud.Estado.BORRADOR
