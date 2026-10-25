import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.users.models import Usuario

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db

ME = "/api/v1/auth/me/"
PASSWORD_URL = "/api/v1/auth/me/password/"


def imagen(formato="PNG", nombre="foto.png", tamano=(10, 10)):
    contenido = io.BytesIO()
    Image.new("RGB", tamano, "blue").save(contenido, formato)
    return SimpleUploadedFile(nombre, contenido.getvalue(), content_type=f"image/{formato.lower()}")


class TestPerfil:
    def test_requiere_sesion(self, api):
        assert api.get(ME).status_code == 401

    def test_devuelve_datos_rol_y_permisos(self, api_como, crear_usuario):
        datos = api_como(crear_usuario("sec", rol="secretario_facultad")).get(ME).json()

        assert datos["rol"] == {"codigo": "secretario_facultad", "nombre": "Secretario(a) Facultad", "ambito": "facultad"}
        assert "solicitudes.editar" in datos["permisos"]
        assert "usuarios.crear" not in datos["permisos"]

    def test_superadmin_recibe_comodin(self, api_como, superadmin):
        assert api_como(superadmin).get(ME).json()["permisos"] == ["*"]

    def test_edita_celular(self, api_como, aspirante):
        response = api_como(aspirante).patch(ME, {"celular": "55000000"}, format="json")

        assert response.status_code == 200
        aspirante.refresh_from_db()
        assert aspirante.celular == "55000000"

    def test_no_puede_cambiar_email_ni_ci(self, api_como, aspirante):
        api_como(aspirante).patch(ME, {"email": "otro@nauta.cu", "ci": "11111111111"}, format="json")

        aspirante.refresh_from_db()
        assert aspirante.email == "maria@nauta.cu"
        assert aspirante.ci == "98042512345"

    def test_sube_foto(self, api_como, aspirante):
        response = api_como(aspirante).patch(ME, {"foto": imagen()}, format="multipart")

        assert response.status_code == 200
        assert response.json()["foto"]

    def test_rechaza_archivo_que_no_es_imagen(self, api_como, aspirante):
        falso = SimpleUploadedFile("foto.png", b"no soy una imagen", content_type="image/png")

        response = api_como(aspirante).patch(ME, {"foto": falso}, format="multipart")

        assert "foto" in response.json()["error"]["detalles"]

    def test_rechaza_formato_no_permitido(self, api_como, aspirante):
        response = api_como(aspirante).patch(ME, {"foto": imagen("GIF", "foto.gif")}, format="multipart")

        assert "foto" in response.json()["error"]["detalles"]

    def test_rechaza_imagen_mayor_de_5_mb(self, api_como, aspirante, monkeypatch):
        monkeypatch.setattr("apps.users.validators.MAX_IMAGEN_MB", 0)

        response = api_como(aspirante).patch(ME, {"foto": imagen()}, format="multipart")

        assert "no puede superar" in response.json()["error"]["detalles"]["foto"][0]


class TestCambiarPassword:
    def test_cambia_la_contrasena(self, api_como, aspirante):
        response = api_como(aspirante).post(PASSWORD_URL, {"actual": PASSWORD, "nueva": "Otra-Clave-456"}, format="json")

        assert response.status_code == 204
        aspirante.refresh_from_db()
        assert aspirante.check_password("Otra-Clave-456")

    def test_exige_la_contrasena_actual(self, api_como, aspirante):
        response = api_como(aspirante).post(PASSWORD_URL, {"actual": "mal", "nueva": "Otra-Clave-456"}, format="json")

        assert "actual" in response.json()["error"]["detalles"]

    def test_valida_la_nueva(self, api_como, aspirante):
        response = api_como(aspirante).post(PASSWORD_URL, {"actual": PASSWORD, "nueva": "123"}, format="json")

        assert "nueva" in response.json()["error"]["detalles"]

    def test_usuario_sgu_no_tiene_contrasena_local(self, api_como, crear_usuario):
        profe = crear_usuario("profe", rol="secretario_facultad", origen=Usuario.Origen.SGU)

        response = api_como(profe).post(PASSWORD_URL, {"actual": PASSWORD, "nueva": "Otra-Clave-456"}, format="json")

        assert response.status_code == 400
        assert "Sistema de Gestión de Usuarios" in response.json()["error"]["mensaje"]
