from datetime import timedelta
from io import BytesIO

import pytest
from django.utils import timezone

from apps.aspirantes import services as aspirantes
from apps.aspirantes.models import TipoDocumento
from apps.aspirantes.tests.fixtures import pdf, png
from apps.auditoria.models import LogAuditoria
from apps.core.exceptions import ErrorDeNegocio
from apps.core.pdf import pdf_disponible
from apps.notificaciones.models import Notificacion
from apps.otorgamiento import services as otorgamiento_services
from apps.otorgamiento.models import Otorgamiento
from apps.otorgamiento.tests.test_otorgamiento import escenario, otorgamiento, usuarios  # noqa: F401 (fixtures)
from apps.prematricula import services
from apps.prematricula.models import ArchivoPrematricula, CampoPrematricula, ElementoPrematricula, PeriodoPrematricula, Prematricula

pytestmark = pytest.mark.django_db

HOY = timezone.localdate()
ADMIN = "/api/v1/admin/prematricula/"
PROPIA = "/api/v1/prematricula/"


@pytest.fixture
def publicado(usuarios, otorgamiento):  # noqa: F811
    otorgamiento_services.aprobar(usuarios["jefe"], otorgamiento)
    return otorgamiento_services.publicar(usuarios["vicerrector"], otorgamiento, segunda_convocatoria=False)


@pytest.fixture
def periodo(usuarios, publicado, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        return services.configurar_periodo(usuarios["secretaria"], publicado, HOY, HOY + timedelta(days=10))


@pytest.fixture
def de_ana(periodo, escenario):  # noqa: F811
    return Prematricula.objects.get(aspirante=escenario["ana"].aspirante)


def elemento(prematricula, nombre):
    return next(e for e in prematricula.elementos.select_related("campo", "tipo_documento") if e.nombre == nombre)


def completar(api_como, prematricula):
    client = api_como(prematricula.aspirante)
    client.post(f"{PROPIA}{prematricula.pk}/archivo/", {"elemento": elemento(prematricula, "Foto tipo carné").pk, "archivo": png()}, format="multipart")
    for nombre in ("Carta de autorización del centro de trabajo", "Solicitud personal firmada"):
        client.post(f"{PROPIA}{prematricula.pk}/archivo/", {"elemento": elemento(prematricula, nombre).pk, "archivo": pdf()}, format="multipart")
    return client


class TestPeriodo:
    def test_solo_la_secretaria_general(self, api_como, usuarios, publicado):
        datos = {"otorgamiento": publicado.pk, "fecha_inicio": str(HOY), "fecha_cierre": str(HOY + timedelta(days=10))}

        assert api_como(usuarios["jefe"]).post(f"{ADMIN}configurar-periodo/", datos, format="json").status_code == 403
        assert api_como(usuarios["secretaria"]).post(f"{ADMIN}configurar-periodo/", datos, format="json").status_code == 201

    def test_exige_el_otorgamiento_publicado(self, usuarios, otorgamiento):  # noqa: F811
        with pytest.raises(ErrorDeNegocio, match="publicado"):
            services.configurar_periodo(usuarios["secretaria"], otorgamiento, HOY, HOY + timedelta(days=5))

    def test_crea_un_expediente_por_otorgado_y_avisa(self, periodo, publicado):
        prematriculas = Prematricula.objects.all()

        assert prematriculas.count() == 3
        assert sorted(e.nombre for e in prematriculas.first().elementos.all()) == sorted(
            ["CI anverso", "CI reverso", "Certificación de estudios", "Foto tipo carné", "Carta de autorización del centro de trabajo", "Solicitud personal firmada"]
        )
        assert Otorgamiento.objects.get(pk=publicado.pk).publico_hasta == periodo.fecha_cierre
        assert Notificacion.objects.filter(tipo="prematricula_abierta").count() == 3


class TestAspirante:
    def test_ve_la_suya_con_los_documentos_del_perfil_reutilizados(self, api_como, de_ana):
        datos = api_como(de_ana.aspirante).get(f"{PROPIA}{de_ana.pk}/").json()

        ci = next(e for e in datos["elementos"] if e["nombre"] == "CI anverso")
        assert (ci["tipo"], ci["entregado"], ci["editable"]) == ("documento_perfil", True, False)
        assert ci["archivo"]["archivo"].startswith("/documentos/")
        assert set(datos["faltantes"]) == {"Foto tipo carné", "Carta de autorización del centro de trabajo", "Solicitud personal firmada"}

    def test_otro_aspirante_no_la_ve(self, api_como, de_ana, escenario):  # noqa: F811
        assert api_como(escenario["luis"].aspirante).get(f"{PROPIA}{de_ana.pk}/").status_code == 404

    def test_la_foto_tipo_carne_es_imagen(self, api_como, de_ana):
        response = api_como(de_ana.aspirante).post(
            f"{PROPIA}{de_ana.pk}/archivo/", {"elemento": elemento(de_ana, "Foto tipo carné").pk, "archivo": pdf()}, format="multipart"
        )

        assert response.status_code == 400

    def test_enviar_exige_lo_requerido(self, api_como, de_ana):
        client = api_como(de_ana.aspirante)

        faltan = client.post(f"{PROPIA}{de_ana.pk}/enviar/")
        assert "Falta entregar" in faltan.json()["error"]["mensaje"]

        completar(api_como, de_ana)
        assert Prematricula.objects.get(pk=de_ana.pk).estado == "borrador"
        response = client.post(f"{PROPIA}{de_ana.pk}/enviar/")
        assert (response.status_code, response.json()["estado"]) == (200, "completada")

        otra = client.post(f"{PROPIA}{de_ana.pk}/archivo/", {"elemento": elemento(de_ana, "Solicitud personal firmada").pk, "archivo": pdf()}, format="multipart")
        assert otra.status_code == 400  # enviada: espera la revisión

    def test_sustituir_crea_versiones(self, api_como, de_ana):
        client = api_como(de_ana.aspirante)
        carta = elemento(de_ana, "Carta de autorización del centro de trabajo")
        for nombre in ("v1.pdf", "v2.pdf"):
            client.post(f"{PROPIA}{de_ana.pk}/archivo/", {"elemento": carta.pk, "archivo": pdf(nombre)}, format="multipart")

        assert list(ArchivoPrematricula.objects.filter(elemento=carta).order_by("version").values_list("version", "vigente")) == [(1, False), (2, True)]

    def test_cuota_propia_de_20_mb(self, de_ana):
        carta = elemento(de_ana, "Carta de autorización del centro de trabajo")
        ArchivoPrematricula.objects.create(elemento=carta, version=1, archivo="x.pdf", nombre_original="x.pdf", formato="PDF", tamano=19 * 1024 * 1024)

        with pytest.raises(ErrorDeNegocio, match="20 MB de la prematrícula"):
            services.subir_archivo(de_ana, elemento(de_ana, "Solicitud personal firmada"), pdf(relleno=2 * 1024 * 1024), "PDF")

    def test_antes_del_inicio_no_se_edita(self, api_como, de_ana):
        PeriodoPrematricula.objects.update(fecha_inicio=HOY + timedelta(days=2), fecha_cierre=HOY + timedelta(days=9))

        response = api_como(de_ana.aspirante).post(
            f"{PROPIA}{de_ana.pk}/archivo/", {"elemento": elemento(de_ana, "Foto tipo carné").pk, "archivo": png()}, format="multipart"
        )

        assert "abre el" in response.json()["error"]["mensaje"]


class TestRevision:
    @pytest.fixture
    def enviada(self, api_como, de_ana):
        completar(api_como, de_ana).post(f"{PROPIA}{de_ana.pk}/enviar/")
        return Prematricula.objects.get(pk=de_ana.pk)

    def revisar(self, client, prematricula, nombre, revision, observacion=""):
        return client.post(f"{ADMIN}{prematricula.pk}/revisar/", {"elemento": elemento(prematricula, nombre).pk, "revision": revision, "observacion": observacion}, format="json")

    def test_la_entidad_de_la_plaza_revisa_y_otra_no(self, api_como, usuarios, enviada):
        assert self.revisar(api_como(usuarios["sec_fac"]), enviada, "Foto tipo carné", "aprobado").status_code == 200
        assert self.revisar(api_como(usuarios["sec_cum"]), enviada, "Foto tipo carné", "aprobado").status_code == 404

    def test_rechazar_exige_observacion(self, api_como, usuarios, enviada):
        assert self.revisar(api_como(usuarios["sec_fac"]), enviada, "CI anverso", "rechazado").status_code == 400

    def test_correccion_aprobacion_y_avisos(self, api_como, usuarios, enviada, django_capture_on_commit_callbacks):
        sec = api_como(usuarios["sec_fac"])
        self.revisar(sec, enviada, "CI anverso", "rechazado", "Ilegible")
        with django_capture_on_commit_callbacks(execute=True):
            response = sec.post(f"{ADMIN}{enviada.pk}/solicitar-correcciones/")
        assert response.json()["estado"] == "con_correcciones"
        assert "CI anverso: Ilegible" in Notificacion.objects.get(tipo="prematricula_correccion").cuerpo

        # El aspirante corrige solo el CI anverso, en su perfil (congelado por ser otorgado).
        aspirante = enviada.aspirante
        aspirantes.subir_documento(aspirante, TipoDocumento.objects.get(nombre="CI anverso"), pdf("ci-nuevo.pdf"), "PDF")
        with pytest.raises(ErrorDeNegocio):
            aspirantes.subir_documento(aspirante, TipoDocumento.objects.get(nombre="CI reverso"), pdf(), "PDF")
        assert elemento(enviada, "CI anverso").revision == "pendiente"
        api_como(aspirante).post(f"{PROPIA}{enviada.pk}/enviar/")

        sec = api_como(usuarios["sec_fac"])
        assert "todos los requeridos" in sec.post(f"{ADMIN}{enviada.pk}/aprobar/").json()["error"]["mensaje"]
        for e in Prematricula.objects.get(pk=enviada.pk).elementos.all():
            self.revisar(sec, enviada, e.nombre, "aprobado")
        with django_capture_on_commit_callbacks(execute=True):
            response = sec.post(f"{ADMIN}{enviada.pk}/aprobar/")

        assert response.json()["estado"] == "aprobada"
        aprobada = Prematricula.objects.get(pk=enviada.pk)
        assert (aprobada.aprobado_por, aprobada.fecha_aprobacion is not None) == (usuarios["sec_fac"], True)
        assert Notificacion.objects.filter(usuario=aspirante, tipo="prematricula_aprobada").exists()

    def test_descarga_auditada_por_la_entidad_de_la_plaza(self, api_como, usuarios, enviada):
        archivo = ArchivoPrematricula.objects.filter(elemento__prematricula=enviada, vigente=True).first()

        assert api_como(usuarios["sec_fac"]).get(f"/api/v1/prematricula/archivos/{archivo.pk}/").status_code == 200
        assert api_como(usuarios["sec_cum"]).get(f"/api/v1/prematricula/archivos/{archivo.pk}/").status_code == 404
        assert LogAuditoria.objects.filter(accion="descargar archivo de prematrícula").count() == 1


class TestTareaDiaria:
    def test_recordatorios_a_5_y_1_dias_una_vez(self, periodo, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            services.tarea_diaria(hoy=periodo.fecha_cierre - timedelta(days=5))
            services.tarea_diaria(hoy=periodo.fecha_cierre - timedelta(days=5))
            services.tarea_diaria(hoy=periodo.fecha_cierre - timedelta(days=1))

        assert Notificacion.objects.filter(tipo="prematricula_recordatorio").count() == 6

    def test_tras_el_cierre_queda_incompleta_sin_perder_la_plaza(self, periodo, de_ana):
        services.tarea_diaria(hoy=periodo.fecha_cierre + timedelta(days=1))

        assert Prematricula.objects.get(pk=de_ana.pk).estado == "incompleta"
        assert de_ana.resultado.otorgada is not None

    def test_tras_el_cierre_solo_se_corrige_lo_rechazado(self, api_como, usuarios, de_ana):
        completar(api_como, de_ana).post(f"{PROPIA}{de_ana.pk}/enviar/")
        services.revisar_elemento(usuarios["sec_fac"], de_ana, elemento(de_ana, "Solicitud personal firmada"), "rechazado", "Sin firma")
        services.solicitar_correcciones(usuarios["sec_fac"], de_ana)
        PeriodoPrematricula.objects.update(fecha_inicio=HOY - timedelta(days=10), fecha_cierre=HOY - timedelta(days=1))
        de_ana.refresh_from_db()

        assert services.puede_editar_elemento(de_ana, elemento(de_ana, "Solicitud personal firmada")) is True
        assert services.puede_editar_elemento(de_ana, elemento(de_ana, "Carta de autorización del centro de trabajo")) is False


class TestPanel:
    def test_filtro_por_faltante_y_exportacion(self, api_como, usuarios, de_ana):
        foto = CampoPrematricula.objects.get(nombre="Foto tipo carné")
        api_como(de_ana.aspirante).post(f"{PROPIA}{de_ana.pk}/archivo/", {"elemento": elemento(de_ana, "Foto tipo carné").pk, "archivo": png()}, format="multipart")
        jefe = api_como(usuarios["jefe"])

        assert jefe.get(ADMIN, {"falta_campo": foto.pk}).json()["count"] == 2
        local = api_como(usuarios["sec_cum"]).get(ADMIN).json()
        assert {p["entidad"] for p in local["results"]} == {"CUM Calixto García"}

        from openpyxl import load_workbook

        response = jefe.get(f"{ADMIN}exportar-excel/")
        filas = list(load_workbook(BytesIO(response.content)).active.values)
        assert any("Pendiente" in [str(v) for v in fila] for fila in filas) or any("Borrador" in [str(v) for v in fila] for fila in filas)
        assert LogAuditoria.objects.filter(accion="exportar prematrículas (Excel)").exists()

    def test_el_superadmin_gestiona_los_campos(self, api_como, superadmin, usuarios):
        url = "/api/v1/admin/campos-prematricula/"

        assert api_como(superadmin).post(url, {"nombre": "Dirección particular", "tipo": "texto", "requerido": False}, format="json").status_code == 201
        assert api_como(usuarios["jefe"]).post(url, {"nombre": "X", "tipo": "texto"}, format="json").status_code == 403
        assert ElementoPrematricula.objects.count() == 0


@pytest.mark.skipif(not pdf_disponible(), reason="WeasyPrint sin librerías nativas (Pango/GTK)")
def test_exportar_pdf(api_como, usuarios, de_ana):
    response = api_como(usuarios["jefe"]).get(f"{ADMIN}exportar-pdf/")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
