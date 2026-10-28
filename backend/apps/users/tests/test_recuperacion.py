import re

import pytest
from django.core import mail
from django.test import override_settings

from apps.core.exceptions import ErrorDeNegocio
from apps.users.models import Usuario
from apps.users.services import recuperacion

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db

RECUPERAR = "/api/v1/auth/recuperar/"
RESTABLECER = "/api/v1/auth/restablecer/"
LOGIN = "/api/v1/auth/login/"
NUEVA = "Otra-Clave-Segura-456"


def pedir(api, email, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        return api.post(RECUPERAR, {"email": email}, format="json")


def datos_del_enlace(correo):
    uid, token = re.search(r"/restablecer\?uid=([\w-]+)&token=([\w-]+)", correo.body).groups()
    return {"uid": uid, "token": token}


def restablecer(api, enlace, password=NUEVA):
    return api.post(RESTABLECER, enlace | {"password": password}, format="json")


class TestSolicitar:
    def test_envia_el_enlace_al_correo_de_la_cuenta(self, api, aspirante, django_capture_on_commit_callbacks):
        response = pedir(api, "MARIA@nauta.cu", django_capture_on_commit_callbacks)

        assert response.status_code == 200
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["maria@nauta.cu"]
        assert "http://localhost:5173/restablecer?uid=" in mail.outbox[0].body

    def test_misma_respuesta_si_el_correo_no_existe(self, api, aspirante, django_capture_on_commit_callbacks):
        existe = pedir(api, "maria@nauta.cu", django_capture_on_commit_callbacks)
        no_existe = pedir(api, "nadie@nauta.cu", django_capture_on_commit_callbacks)

        assert (no_existe.status_code, no_existe.json()) == (existe.status_code, existe.json())
        assert len(mail.outbox) == 1

    def test_usuario_interno_con_correo(self, api, crear_usuario, django_capture_on_commit_callbacks):
        crear_usuario("secretario", rol="jefe_ci", email="secretario@uho.edu.cu")

        pedir(api, "secretario@uho.edu.cu", django_capture_on_commit_callbacks)

        assert mail.outbox[0].to == ["secretario@uho.edu.cu"]

    @pytest.mark.parametrize(
        "cambio",
        [{"is_active": False}, {"origen": Usuario.Origen.SGU}, {"email_verificado": False}],
        ids=["bloqueado", "sgu", "sin_activar"],
    )
    def test_no_envia_a_cuentas_que_no_pueden_recuperarse(self, api, aspirante, cambio, django_capture_on_commit_callbacks):
        Usuario.objects.filter(pk=aspirante.pk).update(**cambio)

        response = pedir(api, "maria@nauta.cu", django_capture_on_commit_callbacks)

        assert response.status_code == 200
        assert mail.outbox == []

    def test_correo_invalido(self, api):
        assert api.post(RECUPERAR, {"email": "no-es-correo"}, format="json").status_code == 400


class TestRestablecer:
    @pytest.fixture
    def enlace(self, api, aspirante, django_capture_on_commit_callbacks):
        pedir(api, "maria@nauta.cu", django_capture_on_commit_callbacks)
        return datos_del_enlace(mail.outbox[0])

    def test_cambia_la_contrasena(self, api, enlace):
        response = restablecer(api, enlace)

        assert response.status_code == 200
        assert api.post(LOGIN, {"identificador": "maria@nauta.cu", "password": NUEVA}, format="json").status_code == 200
        assert api.post(LOGIN, {"identificador": "maria@nauta.cu", "password": PASSWORD}, format="json").status_code == 401

    def test_el_enlace_solo_sirve_una_vez(self, api, enlace):
        restablecer(api, enlace)

        response = restablecer(api, enlace, "Tercera-Clave-789")

        assert response.status_code == 400
        assert "no es válido" in response.json()["error"]["mensaje"]

    def test_token_alterado(self, api, enlace):
        response = restablecer(api, enlace | {"token": enlace["token"][:-2] + "xx"})

        assert response.status_code == 400

    @pytest.mark.parametrize("uid", ["", "basura", "MTIzNDU2Nzg5"])
    def test_uid_invalido(self, api, enlace, uid):
        assert restablecer(api, enlace | {"uid": uid}).status_code == 400

    def test_enlace_caducado(self, api, enlace):
        with override_settings(PASSWORD_RESET_TIMEOUT=-1):
            assert restablecer(api, enlace).status_code == 400

    def test_valida_la_contrasena_nueva(self, api, enlace):
        response = restablecer(api, enlace, "123")

        assert response.status_code == 400
        assert "password" in response.json()["error"]["detalles"]

    def test_quita_el_bloqueo_por_intentos(self, api, aspirante, enlace):
        for _ in range(6):
            api.post(LOGIN, {"identificador": "maria@nauta.cu", "password": "mala"}, format="json")

        restablecer(api, enlace)

        assert api.post(LOGIN, {"identificador": "maria@nauta.cu", "password": NUEVA}, format="json").status_code == 200

    def test_cierra_las_sesiones_abiertas(self, api, aspirante, django_capture_on_commit_callbacks):
        # La sesión se abre antes de pedir el enlace: iniciar sesión después lo invalida.
        api.post(LOGIN, {"identificador": "maria@nauta.cu", "password": PASSWORD}, format="json")
        pedir(api, "maria@nauta.cu", django_capture_on_commit_callbacks)

        assert restablecer(api, datos_del_enlace(mail.outbox[0])).status_code == 200
        assert api.post("/api/v1/auth/refresh/").status_code == 401

    def test_iniciar_sesion_invalida_el_enlace(self, api, enlace):
        api.post(LOGIN, {"identificador": "maria@nauta.cu", "password": PASSWORD}, format="json")

        assert restablecer(api, enlace).status_code == 400

    def test_el_enlace_se_comprueba_otra_vez_con_la_fila_bloqueada(self, aspirante, enlace):
        # Dos peticiones simultáneas con el mismo enlace pasan la validación antes
        # de que ninguna cambie la contraseña; solo la primera debe aplicarse.
        usuario = recuperacion.usuario_del_enlace(enlace["uid"], enlace["token"])
        recuperacion.restablecer(usuario, enlace["token"], NUEVA)

        with pytest.raises(ErrorDeNegocio):
            recuperacion.restablecer(usuario, enlace["token"], "Tercera-Clave-789")
        aspirante.refresh_from_db()
        assert aspirante.check_password(NUEVA)

    def test_cuenta_bloqueada_despues_de_pedirlo(self, api, aspirante, enlace):
        Usuario.objects.filter(pk=aspirante.pk).update(is_active=False)

        assert restablecer(api, enlace).status_code == 400
