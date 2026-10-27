from datetime import timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from django.core import mail

from apps.aspirantes.tests.fixtures import ANIO, HOY, cerrar
from apps.auditoria.models import LogAuditoria
from apps.convocatorias.models import ConvocatoriaSolicitud
from apps.convocatorias.services import ofertas_de
from apps.notificaciones.models import Notificacion
from apps.otorgamiento import services
from apps.otorgamiento.models import Otorgamiento, ResultadoOtorgamiento
from apps.solicitudes import revision
from apps.solicitudes import services as solicitudes
from apps.solicitudes.models import Solicitud, SolicitudCarrera

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/otorgamiento/"


@pytest.fixture
def usuarios(crear_usuario, facultad, cum):
    return {
        "secretaria": crear_usuario("sg", rol="secretaria_general"),
        "jefe": crear_usuario("jefe", rol="jefe_ci"),
        "vicerrector": crear_usuario("vr", rol="vicerrector"),
        "sec_fac": crear_usuario("sec_fac", rol="secretario_facultad", facultad=facultad),
        "sec_cum": crear_usuario("sec_cum", rol="secretario_cum", cum_fum=cum),
    }


@pytest.fixture
def escenario(usuarios, crear_aspirante, completar_perfil, convocatoria, ofertas):
    """Cuatro aspirantes con Informática en la Facultad (80 plazas) reducida a 1 plaza para el ejemplo.

    - Ana (95): Informática Facultad, Derecho CUM.
    - Luis (90): Informática Facultad, Informática CUM.
    - Eva (90, confirmó después que Luis): Informática Facultad, Derecho CUM.
    - Pepe (99): con una observación sin resolver → no elegible.
    """
    ofertas["informatica_facultad"].plazas_plan = 1
    ofertas["informatica_facultad"].save()
    ofertas["informatica_cum"].plazas_plan = 1
    ofertas["informatica_cum"].save()
    ofertas["derecho_cum"].plazas_plan = 1
    ofertas["derecho_cum"].save()

    datos = [
        ("ana", "90010112341", Decimal("95"), ["informatica_facultad", "derecho_cum"]),
        ("luis", "90010112342", Decimal("90"), ["informatica_facultad", "informatica_cum"]),
        ("eva", "90010112343", Decimal("90"), ["informatica_facultad", "derecho_cum"]),
        ("pepe", "90010112344", Decimal("99"), ["informatica_facultad"]),
    ]
    resultado = {}
    for nombre, ci, indice, elegidas in datos:
        aspirante = crear_aspirante(f"asp_{nombre}", ci=ci, email=f"{nombre}@nauta.cu", first_name=nombre.capitalize())
        completar_perfil(aspirante)
        solicitud = solicitudes.obtener_o_crear(aspirante)
        solicitudes.guardar_carreras(solicitud, [ofertas[k] for k in elegidas])
        solicitud = solicitudes.confirmar(solicitud)
        revision.validar_indice(usuarios["jefe"], solicitud, indice)
        resultado[nombre] = Solicitud.objects.get(pk=solicitud.pk)
    revision.crear_observacion(usuarios["jefe"], resultado["pepe"], objetivo="foto", texto="Borrosa")
    cerrar(convocatoria)
    return resultado


def generar(client, convocatoria):
    return client.post(URL, {"convocatoria": convocatoria.pk, "confirmar": True}, format="json")


def resultado_de(otorgamiento, solicitud):
    return ResultadoOtorgamiento.objects.get(otorgamiento=otorgamiento, solicitud=solicitud)


def opcion(solicitud, oferta):
    return SolicitudCarrera.objects.get(solicitud=solicitud, oferta=oferta)


@pytest.fixture
def otorgamiento(api_como, usuarios, escenario, convocatoria):
    return Otorgamiento.objects.get(pk=generar(api_como(usuarios["secretaria"]), convocatoria).json()["id"])


class TestGenerar:
    def test_previsualizar_resume_la_elegibilidad(self, api_como, usuarios, escenario, convocatoria):
        datos = api_como(usuarios["secretaria"]).get(f"{URL}previsualizar/", {"convocatoria": convocatoria.pk}).json()

        assert (datos["solicitudes"], datos["elegibles"], datos["no_elegibles"]) == (4, 3, 1)
        assert {"motivo": "Tiene observaciones sin resolver", "cantidad": 1} in datos["motivos"]
        assert datos["plazas"] == 1 + 1 + 10 + 1  # Informática Fac., Informática CUM, Banes y Derecho CUM

    def test_solo_la_secretaria_general(self, api_como, usuarios, escenario, convocatoria):
        assert api_como(usuarios["jefe"]).get(f"{URL}previsualizar/", {"convocatoria": convocatoria.pk}).status_code == 403
        assert generar(api_como(usuarios["jefe"]), convocatoria).status_code == 403

    def test_exige_confirmar(self, api_como, usuarios, escenario, convocatoria):
        response = api_como(usuarios["secretaria"]).post(URL, {"convocatoria": convocatoria.pk, "confirmar": False}, format="json")

        assert response.status_code == 400

    def test_exige_la_convocatoria_cerrada(self, api_como, usuarios, convocatoria):
        assert generar(api_como(usuarios["secretaria"]), convocatoria).status_code == 400

    def test_ranking_y_reparto(self, otorgamiento, escenario, ofertas):
        ana, luis, eva, pepe = (resultado_de(otorgamiento, escenario[n]) for n in ("ana", "luis", "eva", "pepe"))

        # Orden: índice, luego confirmación (Luis antes que Eva). Pepe queda fuera aunque tenga el mejor índice.
        assert [ana.posicion_ranking, luis.posicion_ranking, eva.posicion_ranking] == [1, 2, 3]
        assert (pepe.posicion_ranking, pepe.motivo_exclusion) == (None, "Estado: Observada; Tiene observaciones sin resolver")
        assert (ana.carrera, ana.prioridad, ana.tipo) == ("Ingeniería Informática", 1, "automatica")
        assert (luis.entidad, luis.prioridad) == ("CUM Calixto García", 2)
        assert (eva.carrera, eva.prioridad) == ("Derecho", 2)
        assert ana.indice_utilizado == Decimal("95")
        assert pepe.otorgada is None

    def test_no_se_ejecuta_dos_veces(self, api_como, usuarios, otorgamiento, convocatoria):
        response = generar(api_como(usuarios["secretaria"]), convocatoria)

        assert response.status_code == 400
        assert "no se puede volver a ejecutar" in response.json()["error"]["mensaje"]

    def test_cierra_la_revision(self, otorgamiento, escenario, usuarios):
        with pytest.raises(Exception, match="la revisión está cerrada"):
            revision.validar_indice(usuarios["jefe"], escenario["pepe"], Decimal("98"))

    def test_el_provisional_solo_lo_ven_los_globales(self, api_como, usuarios, otorgamiento, escenario):
        assert api_como(usuarios["sec_fac"]).get(f"{URL}{otorgamiento.pk}/").status_code == 404
        assert api_como(usuarios["vicerrector"]).get(f"{URL}{otorgamiento.pk}/resultados/").json()["count"] == 4
        # El aspirante sigue sin resultado hasta la publicación.
        assert Solicitud.objects.get(pk=escenario["ana"].pk).estado == "en_revision"


class TestAjustes:
    def ajustar(self, client, otorgamiento, resultado, tipo, opcion_, justificacion="Error en el plan"):
        return client.post(
            f"{URL}{otorgamiento.pk}/ajustar/",
            {"resultado": resultado.pk, "tipo": tipo, "opcion": opcion_.pk, "justificacion": justificacion},
            format="json",
        )

    def test_otorgar_resuelve_la_cascada(self, api_como, usuarios, otorgamiento, escenario, ofertas):
        eva = resultado_de(otorgamiento, escenario["eva"])

        response = self.ajustar(api_como(usuarios["jefe"]), otorgamiento, eva, "otorgar", opcion(escenario["eva"], ofertas["informatica_facultad"]))

        # Eva ocupa la única plaza de Informática Facultad; Ana baja a Derecho, que deja libre Eva.
        assert response.status_code == 201
        cambios = {c["aspirante"]: c["despues"] for c in response.json()["cambios"]}
        assert cambios == {
            "Eva González Pérez": "Ingeniería Informática — Facultad de Informática",
            "Ana González Pérez": "Derecho — CUM Calixto García",
        }

    def test_los_ajustes_fijados_nunca_superan_el_plan(self, api_como, usuarios, otorgamiento, escenario, ofertas):
        client = api_como(usuarios["jefe"])
        ana = resultado_de(otorgamiento, escenario["ana"])
        # Fija a Ana donde ya está y luego intenta fijar a Eva en la misma plaza única.
        self.ajustar(client, otorgamiento, ana, "quitar", opcion(escenario["ana"], ofertas["informatica_facultad"]))
        self.ajustar(client, otorgamiento, resultado_de(otorgamiento, escenario["ana"]), "otorgar", opcion(escenario["ana"], ofertas["informatica_facultad"]))
        eva = resultado_de(otorgamiento, escenario["eva"])

        response = self.ajustar(client, otorgamiento, eva, "otorgar", opcion(escenario["eva"], ofertas["informatica_facultad"]))

        assert response.status_code == 400
        assert "No quedan plazas en Ingeniería Informática — Facultad de Informática" in response.json()["error"]["mensaje"]

    def test_quitar_baja_a_la_siguiente_opcion_y_cubre_la_vacante(self, api_como, usuarios, otorgamiento, escenario, ofertas):
        ana = resultado_de(otorgamiento, escenario["ana"])

        response = self.ajustar(api_como(usuarios["jefe"]), otorgamiento, ana, "quitar", opcion(escenario["ana"], ofertas["informatica_facultad"]))

        assert response.status_code == 201
        cambios = {c["aspirante"]: (c["antes"], c["despues"]) for c in response.json()["cambios"]}
        # Ana baja a Derecho; Luis sube a Informática Facultad (su 1.ª); Eva se queda sin plaza.
        assert cambios["Ana González Pérez"][1] == "Derecho — CUM Calixto García"
        assert cambios["Luis González Pérez"][1] == "Ingeniería Informática — Facultad de Informática"
        assert cambios["Eva González Pérez"] == ("Derecho — CUM Calixto García", None)

    def test_otorgar_con_plaza_libre(self, api_como, usuarios, otorgamiento, escenario, ofertas):
        client = api_como(usuarios["jefe"])
        ana = resultado_de(otorgamiento, escenario["ana"])
        self.ajustar(client, otorgamiento, ana, "quitar", opcion(escenario["ana"], ofertas["informatica_facultad"]))
        eva = resultado_de(otorgamiento, escenario["eva"])

        response = self.ajustar(client, otorgamiento, eva, "otorgar", opcion(escenario["eva"], ofertas["derecho_cum"]))

        assert response.status_code == 201
        eva.refresh_from_db()
        assert (eva.carrera, eva.tipo) == ("Derecho", "manual")
        assert resultado_de(otorgamiento, escenario["ana"]).otorgada is None

    def test_anular_un_ajuste_lo_deshace(self, api_como, usuarios, otorgamiento, escenario, ofertas):
        client = api_como(usuarios["jefe"])
        ana = resultado_de(otorgamiento, escenario["ana"])
        ajuste = self.ajustar(client, otorgamiento, ana, "quitar", opcion(escenario["ana"], ofertas["informatica_facultad"])).json()["ajuste"]

        response = client.post(f"{URL}{otorgamiento.pk}/ajustes/{ajuste['id']}/anular/", {"justificacion": "Me equivoqué"}, format="json")

        assert response.status_code == 200
        assert resultado_de(otorgamiento, escenario["ana"]).carrera == "Ingeniería Informática"
        historial = client.get(f"{URL}{otorgamiento.pk}/ajustes/").json()
        assert (historial[0]["activo"], historial[0]["justificacion_anulacion"]) == (False, "Me equivoqué")

    def test_no_a_un_no_elegible(self, api_como, usuarios, otorgamiento, escenario, ofertas):
        pepe = resultado_de(otorgamiento, escenario["pepe"])

        response = self.ajustar(api_como(usuarios["jefe"]), otorgamiento, pepe, "otorgar", opcion(escenario["pepe"], ofertas["informatica_facultad"]))

        assert response.status_code == 400
        assert "no es elegible" in response.json()["error"]["mensaje"]

    def test_solo_carreras_de_su_solicitud(self, api_como, usuarios, otorgamiento, escenario, ofertas):
        ana = resultado_de(otorgamiento, escenario["ana"])

        response = self.ajustar(api_como(usuarios["jefe"]), otorgamiento, ana, "otorgar", opcion(escenario["luis"], ofertas["informatica_cum"]))

        assert response.status_code == 400

    def test_exige_justificacion(self, api_como, usuarios, otorgamiento, escenario, ofertas):
        ana = resultado_de(otorgamiento, escenario["ana"])

        response = self.ajustar(api_como(usuarios["jefe"]), otorgamiento, ana, "quitar", opcion(escenario["ana"], ofertas["informatica_facultad"]), "")

        assert response.status_code == 400

    def test_en_la_revision_del_jefe_ci_el_vicerrector_no_edita(self, api_como, usuarios, otorgamiento, escenario, ofertas):
        ana = resultado_de(otorgamiento, escenario["ana"])

        response = self.ajustar(api_como(usuarios["vicerrector"]), otorgamiento, ana, "quitar", opcion(escenario["ana"], ofertas["informatica_facultad"]))

        assert response.status_code == 400
        assert "Jefe de la Comisión" in response.json()["error"]["mensaje"]


class TestAprobacionYPublicacion:
    @pytest.fixture(autouse=True)
    def _on_commit(self, django_capture_on_commit_callbacks):
        self.capturar = django_capture_on_commit_callbacks

    def test_flujo_completo(self, api_como, usuarios, otorgamiento, escenario, ofertas):
        jefe = api_como(usuarios["jefe"])
        assert jefe.post(f"{URL}{otorgamiento.pk}/publicar/", {"segunda_convocatoria": True}, format="json").status_code == 403

        with self.capturar(execute=True):
            response = jefe.post(f"{URL}{otorgamiento.pk}/aprobar/")
        assert (response.status_code, response.json()["estado"]) == (200, "aprobacion")
        assert Notificacion.objects.filter(usuario=usuarios["vicerrector"], tipo="otorgamiento_para_aprobacion").exists()

        # Ya en manos del Vicerrector: el Jefe CI no edita.
        ana = resultado_de(otorgamiento, escenario["ana"])
        quitar = {"resultado": ana.pk, "tipo": "quitar", "opcion": opcion(escenario["ana"], ofertas["informatica_facultad"]).pk, "justificacion": "x"}
        assert jefe.post(f"{URL}{otorgamiento.pk}/ajustar/", quitar, format="json").status_code == 400

        vicerrector = api_como(usuarios["vicerrector"])
        mail.outbox.clear()
        with self.capturar(execute=True):
            response = vicerrector.post(f"{URL}{otorgamiento.pk}/publicar/", {"segunda_convocatoria": True}, format="json")

        assert (response.status_code, response.json()["estado"]) == (200, "publicado")
        assert Solicitud.objects.get(pk=escenario["ana"].pk).estado == "otorgada"
        assert Solicitud.objects.get(pk=escenario["pepe"].pk).estado == "no_seleccionado"
        estados = dict(SolicitudCarrera.objects.filter(solicitud=escenario["ana"]).values_list("prioridad", "estado"))
        assert estados == {1: "otorgada", 2: "no_seleccionada"}
        avisos = dict(Notificacion.objects.filter(tipo__in=["plaza_otorgada", "no_seleccionado_segunda"]).values_list("usuario__username", "tipo"))
        assert avisos == {"asp_ana": "plaza_otorgada", "asp_luis": "plaza_otorgada", "asp_eva": "plaza_otorgada", "asp_pepe": "no_seleccionado_segunda"}
        assert any("Ingeniería Informática (Facultad de Informática)" in m.body for m in mail.outbox)
        assert any("segunda convocatoria" in m.body for m in mail.outbox)

        # Publicado: congelado.
        assert vicerrector.post(f"{URL}{otorgamiento.pk}/ajustar/", quitar, format="json").status_code == 400

    def test_sin_segunda_convocatoria(self, api_como, usuarios, otorgamiento):
        services.aprobar(usuarios["jefe"], otorgamiento)

        with self.capturar(execute=True):
            services.publicar(usuarios["vicerrector"], otorgamiento, segunda_convocatoria=False)

        assert Notificacion.objects.filter(tipo="no_seleccionado_final").count() == 1

    def test_publicado_la_entidad_ve_lo_suyo(self, api_como, usuarios, otorgamiento):
        services.aprobar(usuarios["jefe"], otorgamiento)
        services.publicar(usuarios["vicerrector"], otorgamiento, True)

        datos = api_como(usuarios["sec_cum"]).get(f"{URL}{otorgamiento.pk}/resultados/").json()

        assert {r["entidad"] for r in datos["results"]} == {"CUM Calixto García"}
        assert datos["count"] == 2

    def test_segunda_convocatoria_con_plazas_restantes(self, api_como, usuarios, otorgamiento, ofertas, convocatoria):
        services.aprobar(usuarios["jefe"], otorgamiento)
        services.publicar(usuarios["vicerrector"], otorgamiento, True)

        response = api_como(usuarios["jefe"]).post(
            "/api/v1/admin/convocatorias/",
            {"anio_academico": ANIO, "fecha_inicio": str(HOY), "fecha_cierre": str(HOY + timedelta(days=10))}, format="json",
        )
        assert (response.status_code, response.json()["numero"]) == (201, 2)
        segunda = ConvocatoriaSolicitud.objects.get(pk=response.json()["id"])

        restantes = services.plazas_restantes(segunda)
        assert restantes[ofertas["informatica_facultad"].pk] == 0
        assert restantes[ofertas["informatica_banes"].pk] == 10
        # En la segunda solo se ofrecen las que conservan plazas.
        assert ofertas["informatica_facultad"].pk not in set(ofertas_de(segunda).values_list("pk", flat=True))

    def test_exportar_excel_auditado(self, api_como, usuarios, otorgamiento):
        from openpyxl import load_workbook

        response = api_como(usuarios["jefe"]).get(f"{URL}{otorgamiento.pk}/exportar-excel/")

        assert response.status_code == 200
        filas = list(load_workbook(BytesIO(response.content)).active.values)
        assert any("No seleccionado" in [str(v) for v in fila] for fila in filas)
        assert LogAuditoria.objects.filter(accion="exportar otorgamiento (Excel)").exists()


def test_el_aspirante_no_seleccionado_puede_ir_a_la_segunda(api_como, usuarios, otorgamiento, escenario, ofertas):
    services.aprobar(usuarios["jefe"], otorgamiento)
    services.publicar(usuarios["vicerrector"], otorgamiento, True)
    segunda = ConvocatoriaSolicitud.objects.create(
        anio_academico=ANIO, numero=2, fecha_inicio=HOY, fecha_cierre=HOY + timedelta(days=5), estado="abierta"
    )

    pepe = escenario["pepe"].aspirante
    nueva = api_como(pepe).post("/api/v1/solicitudes/")
    ana = api_como(escenario["ana"].aspirante).post("/api/v1/solicitudes/")

    assert (nueva.status_code, nueva.json()["convocatoria"]["id"]) == (201, segunda.pk)
    assert ana.status_code == 400  # ya obtuvo plaza: su perfil queda congelado
