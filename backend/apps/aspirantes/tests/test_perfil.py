import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.aspirantes import services
from apps.aspirantes.models import DocumentoAspirante, PerfilAspirante, TipoDocumento
from apps.core.exceptions import ErrorDeNegocio
from apps.solicitudes.models import Solicitud

from .fixtures import cerrar, pdf, png

pytestmark = pytest.mark.django_db

PERFIL = "/api/v1/aspirante/perfil/"
DOCUMENTOS = "/api/v1/aspirante/documentos/"
ME = "/api/v1/auth/me/"
MB = 1024 * 1024


def tipo(nombre):
    return TipoDocumento.objects.get(nombre=nombre)


def requisitos(respuesta):
    return {r["clave"]: r["cumple"] for r in respuesta.json()["requisitos"]}


class TestPerfil:
    def test_solo_para_aspirantes(self, api_como, crear_usuario):
        assert api_como(crear_usuario("sec", rol="secretario_facultad")).get(PERFIL).status_code == 403

    def test_un_perfil_nuevo_dice_lo_que_falta(self, api_como, aspirante):
        response = api_como(aspirante).get(PERFIL)

        assert response.status_code == 200
        assert requisitos(response) == {
            "datos_personales": True, "correo_validado": True, "privacidad": True, "foto": False,
            "centro_trabajo": False, "indice": False, "documentos": False, "carreras": False,
        }
        assert response.json()["perfil_completo"] is False
        assert [d["tipo"]["nombre"] for d in response.json()["documentos"]] == ["CI anverso", "CI reverso", "Certificación de estudios"]

    def test_guarda_centro_de_trabajo_e_indice(self, api_como, aspirante):
        response = api_como(aspirante).patch(PERFIL, {"centro_trabajo": "  Empresa Eléctrica ", "indice_declarado": 91.25}, format="json")

        assert response.status_code == 200
        assert (response.json()["centro_trabajo"], response.json()["indice_declarado"]) == ("Empresa Eléctrica", 91.25)
        assert response.json()["indice_validado"] is None

    def test_el_indice_va_de_0_a_100(self, api_como, aspirante):
        response = api_como(aspirante).patch(PERFIL, {"indice_declarado": 100.5}, format="json")

        assert response.status_code == 400
        assert "indice_declarado" in response.json()["error"]["detalles"]

    def test_el_aspirante_no_fija_el_indice_validado(self, api_como, aspirante):
        api_como(aspirante).patch(PERFIL, {"indice_validado": 99}, format="json")

        assert PerfilAspirante.objects.get(usuario=aspirante).indice_validado is None

    def test_listo_para_carreras_sin_carreras_aun(self, api_como, perfil_listo, aspirante):
        datos = api_como(aspirante).get(PERFIL).json()

        assert datos["limites"]["listo_para_carreras"] is True
        assert datos["perfil_completo"] is False  # falta al menos una carrera

    def test_un_documento_obligatorio_nuevo_deja_el_perfil_incompleto(self, perfil_listo, aspirante):
        TipoDocumento.objects.create(nombre="Aval del centro de trabajo", obligatorio=True)

        assert services.listo_para_carreras(services.perfil_de(aspirante)) is False


class TestDocumentos:
    def test_sube_un_pdf(self, api_como, aspirante):
        response = api_como(aspirante).post(DOCUMENTOS, {"tipo": tipo("Certificación de estudios").pk, "archivo": pdf()}, format="multipart")

        assert response.status_code == 201
        subido = next(d for d in response.json()["documentos"] if d["tipo"]["nombre"] == "Certificación de estudios")["documento"]
        assert (subido["version"], subido["formato"], subido["nombre_original"]) == (1, "PDF", "certificacion.pdf")
        assert subido["archivo"] == f"/documentos/{subido['id']}/archivo/"

    def test_acepta_imagenes_jpg_y_png(self, api_como, aspirante):
        jpg = io.BytesIO()
        Image.new("RGB", (8, 8)).save(jpg, "JPEG")
        client = api_como(aspirante)

        a = client.post(DOCUMENTOS, {"tipo": tipo("CI anverso").pk, "archivo": SimpleUploadedFile("ci.jpg", jpg.getvalue())}, format="multipart")
        b = client.post(DOCUMENTOS, {"tipo": tipo("CI reverso").pk, "archivo": png("ci.png")}, format="multipart")

        assert (a.status_code, b.status_code) == (201, 201)
        assert set(DocumentoAspirante.objects.values_list("formato", flat=True)) == {"JPEG", "PNG"}

    @pytest.mark.parametrize(
        "archivo",
        [
            SimpleUploadedFile("ci.pdf", b"no soy un pdf"),
            SimpleUploadedFile("ci.gif", b"GIF89a\x01\x00\x01\x00\x00\x00\x00;"),
        ],
        ids=["contenido-falso", "gif"],
    )
    def test_rechaza_formatos_no_admitidos(self, api_como, aspirante, archivo):
        response = api_como(aspirante).post(DOCUMENTOS, {"tipo": tipo("CI anverso").pk, "archivo": archivo}, format="multipart")

        assert response.status_code == 400
        assert "archivo" in response.json()["error"]["detalles"]

    def test_maximo_5_mb_por_archivo(self, api_como, aspirante):
        response = api_como(aspirante).post(DOCUMENTOS, {"tipo": tipo("CI anverso").pk, "archivo": pdf(relleno=5 * MB)}, format="multipart")

        assert response.status_code == 400

    def test_sustituir_crea_una_version_nueva_y_conserva_la_anterior(self, api_como, aspirante):
        client = api_como(aspirante)
        certificacion = tipo("Certificación de estudios")
        client.post(DOCUMENTOS, {"tipo": certificacion.pk, "archivo": pdf("v1.pdf")}, format="multipart")
        response = client.post(DOCUMENTOS, {"tipo": certificacion.pk, "archivo": pdf("v2.pdf")}, format="multipart")

        vigente = next(d for d in response.json()["documentos"] if d["tipo"]["id"] == certificacion.pk)["documento"]
        assert (vigente["version"], vigente["nombre_original"]) == (2, "v2.pdf")
        assert list(DocumentoAspirante.objects.order_by("version").values_list("version", "vigente")) == [(1, False), (2, True)]

    def test_conserva_como_maximo_10_versiones(self, aspirante):
        certificacion = tipo("Certificación de estudios")
        for _ in range(11):
            services.subir_documento(aspirante, certificacion, pdf(), "PDF")

        versiones = list(DocumentoAspirante.objects.order_by("version").values_list("version", flat=True))
        assert versiones == list(range(2, 12))

    def test_limite_de_20_mb_entre_los_vigentes(self, aspirante):
        perfil = services.perfil_de(aspirante)
        # Simula 16 MB ya subidos en dos documentos.
        for nombre in ("CI anverso", "CI reverso"):
            DocumentoAspirante.objects.create(perfil=perfil, tipo=tipo(nombre), version=1, archivo="x.pdf", nombre_original="x.pdf", formato="PDF", tamano=8 * MB)

        with pytest.raises(ErrorDeNegocio, match="20 MB"):
            services.subir_documento(aspirante, tipo("Certificación de estudios"), pdf(relleno=4 * MB + 1), "PDF")

    def test_sustituir_no_cuenta_dos_veces_el_mismo_documento(self, aspirante):
        perfil = services.perfil_de(aspirante)
        DocumentoAspirante.objects.create(perfil=perfil, tipo=tipo("CI anverso"), version=1, archivo="x.pdf", nombre_original="x.pdf", formato="PDF", tamano=18 * MB)

        services.subir_documento(aspirante, tipo("CI anverso"), pdf(relleno=MB), "PDF")

        assert DocumentoAspirante.objects.get(vigente=True).version == 2

    def test_un_tipo_inactivo_no_se_sube(self, api_como, aspirante):
        anverso = tipo("CI anverso")
        anverso.activo = False
        anverso.save()

        response = api_como(aspirante).post(DOCUMENTOS, {"tipo": anverso.pk, "archivo": pdf()}, format="multipart")

        assert response.status_code == 400


class TestFoto:
    def test_la_foto_del_aspirante_es_jpg_o_png(self, api_como, aspirante):
        webp = io.BytesIO()
        Image.new("RGB", (8, 8)).save(webp, "WEBP")

        response = api_como(aspirante).patch(ME, {"foto": SimpleUploadedFile("f.webp", webp.getvalue())}, format="multipart")

        assert response.status_code == 400
        assert "JPG, PNG" in str(response.json()["error"]["detalles"]["foto"])

    def test_subir_foto_actualiza_el_perfil_completo(self, api_como, aspirante, completar_perfil):
        completar_perfil(aspirante)
        aspirante.foto.delete()
        assert api_como(aspirante).get(PERFIL).json()["tiene_foto"] is False

        response = api_como(aspirante).patch(ME, {"foto": png()}, format="multipart")

        assert response.status_code == 200
        assert response.json()["foto"].startswith("/auth/me/foto/?v=")
        assert api_como(aspirante).get(PERFIL).json()["tiene_foto"] is True

    def test_mi_foto_se_sirve_con_sesion(self, api, api_como, aspirante):
        api_como(aspirante).patch(ME, {"foto": png()}, format="multipart")

        assert api_como(aspirante).get("/api/v1/auth/me/foto/").status_code == 200
        api.force_authenticate(None)
        assert api.get("/api/v1/auth/me/foto/").status_code == 401


class TestPerfilCongelado:
    def test_con_la_convocatoria_cerrada_no_se_edita(self, api_como, perfil_listo, aspirante, convocatoria):
        Solicitud.objects.create(aspirante=aspirante, convocatoria=convocatoria, estado=Solicitud.Estado.PENDIENTE)
        cerrar(convocatoria)
        client = api_como(aspirante)

        assert client.patch(PERFIL, {"indice_declarado": 99}, format="json").status_code == 400
        assert client.post(DOCUMENTOS, {"tipo": tipo("CI anverso").pk, "archivo": pdf()}, format="multipart").status_code == 400
        assert client.patch(ME, {"foto": png()}, format="multipart").status_code == 400
        assert client.get(PERFIL).json()["bloqueado"] is True

    def test_con_la_convocatoria_abierta_si_se_edita(self, api_como, perfil_listo, aspirante, convocatoria):
        Solicitud.objects.create(aspirante=aspirante, convocatoria=convocatoria, estado=Solicitud.Estado.PENDIENTE)

        assert api_como(aspirante).patch(PERFIL, {"indice_declarado": 99}, format="json").status_code == 200

    def test_un_no_seleccionado_puede_actualizarlo_para_la_siguiente(self, api_como, perfil_listo, aspirante, convocatoria):
        Solicitud.objects.create(aspirante=aspirante, convocatoria=convocatoria, estado=Solicitud.Estado.NO_SELECCIONADO)
        cerrar(convocatoria)

        assert api_como(aspirante).patch(PERFIL, {"indice_declarado": 99}, format="json").status_code == 200

    def test_un_borrador_sin_confirmar_no_lo_congela(self, api_como, perfil_listo, aspirante, convocatoria):
        Solicitud.objects.create(aspirante=aspirante, convocatoria=convocatoria)
        cerrar(convocatoria)

        assert api_como(aspirante).patch(PERFIL, {"indice_declarado": 99}, format="json").status_code == 200
