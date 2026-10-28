import re
from datetime import timedelta

import pytest
from django.core import mail, signing
from django.db import connection
from django.utils import timezone

from apps.users.models import Usuario
from apps.users.services import registro
from apps.users.tasks import eliminar_cuentas_no_verificadas

pytestmark = pytest.mark.django_db

REGISTRO = "/api/v1/auth/registro/"
ACTIVAR = "/api/v1/auth/activar/"


def registrar(api, datos):
    return api.post(REGISTRO, datos, format="json")


def errores(response):
    return response.json()["error"]["detalles"]


class TestRegistro:
    def test_crea_aspirante_sin_activar(self, api, datos_registro, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            response = registrar(api, datos_registro)

        assert response.status_code == 201
        usuario = Usuario.objects.get(rol__codigo="aspirante")
        assert usuario.first_name == "Carlos"
        assert usuario.ci == "96071834521"
        assert not usuario.email_verificado
        assert usuario.privacidad_aceptada_at is not None

    def test_envia_correo_con_enlace_de_activacion(self, api, datos_registro, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            registrar(api, datos_registro)

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["carlos@nauta.cu"]
        assert "http://localhost:5173/activar?token=" in mail.outbox[0].body

    def test_datos_personales_cifrados_en_la_base_de_datos(self, api, datos_registro):
        registrar(api, datos_registro)

        with connection.cursor() as cursor:
            cursor.execute("SELECT ci, email, celular FROM users_usuario")
            fila = " ".join(cursor.fetchone())
        assert "96071834521" not in fila
        assert "carlos@nauta.cu" not in fila
        assert "55987654" not in fila

    def test_exige_aceptar_la_politica_de_privacidad(self, api, datos_registro):
        response = registrar(api, datos_registro | {"acepta_privacidad": False})

        assert response.status_code == 400
        assert "acepta_privacidad" in errores(response)

    @pytest.mark.parametrize("ci", ["1234567890", "123456789012", "9607183452a", "960718 34521"])
    def test_ci_debe_tener_11_digitos(self, api, datos_registro, ci):
        assert "ci" in errores(registrar(api, datos_registro | {"ci": ci}))

    @pytest.mark.parametrize("celular", ["45123456", "5512345", "551234567"])
    def test_celular_valido(self, api, datos_registro, celular):
        assert "celular" in errores(registrar(api, datos_registro | {"celular": celular}))

    def test_ci_unico(self, api, datos_registro, aspirante):
        response = registrar(api, datos_registro | {"ci": aspirante.ci})

        assert "Ya existe una cuenta" in errores(response)["ci"][0]

    @pytest.mark.parametrize("campo", ["ci", "email"])
    def test_registro_simultaneo_duplicado_da_400(self, api, datos_registro, aspirante, monkeypatch, campo):
        # Simula la carrera: la validación previa no ve la otra cuenta y choca con la restricción única.
        from apps.users.serializers import RegistroSerializer

        monkeypatch.setattr(RegistroSerializer, f"validate_{campo}", lambda self, valor: valor)
        duplicado = {"ci": aspirante.ci, "email": aspirante.email}[campo]

        response = registrar(api, datos_registro | {campo: duplicado})

        assert response.status_code == 400
        assert "Ya existe una cuenta" in errores(response)[campo][0]

    def test_email_unico_sin_distinguir_mayusculas(self, api, datos_registro, aspirante):
        response = registrar(api, datos_registro | {"email": "MARIA@nauta.cu"})

        assert "email" in errores(response)

    def test_rechaza_contrasenas_debiles(self, api, datos_registro):
        assert "password" in errores(registrar(api, datos_registro | {"password": "123"}))


class TestActivacion:
    def _token(self, api, datos, capturar):
        with capturar(execute=True):
            registrar(api, datos)
        return re.search(r"token=(\S+)", mail.outbox[0].body).group(1)

    def test_activa_la_cuenta(self, api, datos_registro, django_capture_on_commit_callbacks):
        token = self._token(api, datos_registro, django_capture_on_commit_callbacks)

        response = api.post(ACTIVAR, {"token": token}, format="json")

        assert response.status_code == 200
        assert Usuario.objects.get(rol__codigo="aspirante").email_verificado

    def test_tras_activar_puede_iniciar_sesion(self, api, datos_registro, django_capture_on_commit_callbacks):
        token = self._token(api, datos_registro, django_capture_on_commit_callbacks)
        api.post(ACTIVAR, {"token": token}, format="json")

        response = api.post(
            "/api/v1/auth/login/",
            {"identificador": datos_registro["email"], "password": datos_registro["password"]},
            format="json",
        )
        assert response.status_code == 200

    def test_token_invalido(self, api):
        response = api.post(ACTIVAR, {"token": "manipulado"}, format="json")

        assert response.status_code == 400
        assert "no es válido" in response.json()["error"]["mensaje"]

    def test_token_caducado(self, api, aspirante, settings):
        token = registro.generar_token_activacion(aspirante)
        settings.ACTIVACION_HORAS = 0

        response = api.post(ACTIVAR, {"token": token}, format="json")

        assert "caducó" in response.json()["error"]["mensaje"]

    def test_cuenta_ya_eliminada(self, api):
        token = signing.dumps({"u": 999}, salt="users.activacion")

        assert "ya no existe" in api.post(ACTIVAR, {"token": token}, format="json").json()["error"]["mensaje"]


class TestLimpiezaDeCuentas:
    def _aspirante(self, datos, horas, verificado=False):
        usuario = registro.registrar_aspirante(
            nombre=datos["nombre"], apellidos=datos["apellidos"], ci=datos["ci"],
            email=datos["email"], celular=datos["celular"], password=datos["password"],
        )
        Usuario.objects.filter(pk=usuario.pk).update(
            date_joined=timezone.now() - timedelta(hours=horas), email_verificado=verificado
        )
        return usuario

    def test_elimina_cuentas_sin_activar_pasadas_48_horas(self, datos_registro):
        vieja = self._aspirante(datos_registro, horas=49)

        assert eliminar_cuentas_no_verificadas() == 1
        assert not Usuario.objects.filter(pk=vieja.pk).exists()

    def test_conserva_cuentas_recientes_o_activadas(self, datos_registro):
        self._aspirante(datos_registro, horas=47)
        otra = datos_registro | {"ci": "00052315678", "email": "ana@nauta.cu"}
        self._aspirante(otra, horas=100, verificado=True)

        assert eliminar_cuentas_no_verificadas() == 0
        assert Usuario.objects.filter(rol__codigo="aspirante").count() == 2

    def test_no_elimina_usuarios_internos(self, crear_usuario):
        interno = crear_usuario("jcastro", rol="jefe_ci")
        Usuario.objects.filter(pk=interno.pk).update(date_joined=timezone.now() - timedelta(days=10))

        assert eliminar_cuentas_no_verificadas() == 0
