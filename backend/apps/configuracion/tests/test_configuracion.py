import smtplib

import pytest
from django.core import mail
from django.db import connection

from apps.configuracion import plantillas, services
from apps.configuracion.models import ConfiguracionSistema, ConfiguracionSMTP, IdentidadVisual, PlantillaCorreo

pytestmark = pytest.mark.django_db

BASE = "/api/v1/admin/configuracion"


@pytest.fixture
def jefe_ci(crear_usuario):
    return crear_usuario("jefe", rol="jefe_ci")


@pytest.fixture
def con_lectura(crear_usuario):
    """Rol propio con configuracion.ver pero sin ser Superadmin."""
    from apps.roles.models import Permiso, Rol

    rol = Rol.objects.create(codigo="observador", nombre="Observador", ambito="global")
    rol.permisos.set(Permiso.objects.filter(modulo="configuracion"))
    return crear_usuario("obs", rol=rol)


class TestPermisos:
    @pytest.mark.parametrize("ruta", ["parametros", "smtp", "identidad", "plantillas"])
    def test_sin_permiso_no_ve_la_configuracion(self, api_como, jefe_ci, ruta):
        assert api_como(jefe_ci).get(f"{BASE}/{ruta}/").status_code == 403

    def test_con_permiso_de_lectura_ve_pero_no_modifica(self, api_como, con_lectura):
        client = api_como(con_lectura)

        assert client.get(f"{BASE}/parametros/").status_code == 200
        response = client.patch(f"{BASE}/parametros/", {"max_carreras_aspirante": 3}, format="json")
        assert response.status_code == 403
        assert "Superadmin" in response.json()["error"]["mensaje"]

    def test_superadmin_modifica(self, api_como, superadmin):
        response = api_como(superadmin).patch(f"{BASE}/parametros/", {"max_carreras_aspirante": 3}, format="json")

        assert response.status_code == 200
        config = ConfiguracionSistema.actual()
        assert config.max_carreras_aspirante == 3
        assert config.actualizado_por == superadmin

    @pytest.mark.parametrize("ruta", ["parametros", "smtp", "identidad"])
    def test_put_no_esta_disponible(self, api_como, superadmin, con_lectura, ruta):
        assert api_como(superadmin).put(f"{BASE}/{ruta}/", {}, format="json").status_code == 405
        assert api_como(con_lectura).put(f"{BASE}/{ruta}/", {}, format="json").status_code == 405


class TestParametros:
    def test_valores_por_defecto(self, api_como, superadmin):
        datos = api_como(superadmin).get(f"{BASE}/parametros/").json()

        assert (datos["max_carreras_aspirante"], datos["login_max_intentos"], datos["login_bloqueo_minutos"]) == (5, 5, 15)

    def test_limites(self, api_como, superadmin):
        response = api_como(superadmin).patch(f"{BASE}/parametros/", {"max_carreras_aspirante": 0}, format="json")

        assert "max_carreras_aspirante" in response.json()["error"]["detalles"]

    def test_es_una_sola_fila(self):
        ConfiguracionSistema(max_carreras_aspirante=4).save()
        ConfiguracionSistema(max_carreras_aspirante=6).save()

        assert ConfiguracionSistema.objects.count() == 1
        assert ConfiguracionSistema.actual().max_carreras_aspirante == 6


class TestSmtp:
    def test_la_contrasena_nunca_se_devuelve(self, api_como, superadmin):
        response = api_como(superadmin).patch(
            f"{BASE}/smtp/", {"host": "smtp.uho.edu.cu", "password": "secreta", "remitente": "a@uho.edu.cu"}, format="json"
        )

        assert "password" not in response.json()
        assert response.json()["password_configurada"] is True
        assert "secreta" not in api_como(superadmin).get(f"{BASE}/smtp/").content.decode()

    def test_la_contrasena_se_guarda_cifrada(self, api_como, superadmin):
        api_como(superadmin).patch(f"{BASE}/smtp/", {"password": "secreta"}, format="json")

        with connection.cursor() as cursor:
            cursor.execute("SELECT password FROM configuracion_configuracionsmtp")
            assert "secreta" not in cursor.fetchone()[0]
        assert ConfiguracionSMTP.actual().password == "secreta"

    def test_password_vacia_conserva_la_guardada(self, api_como, superadmin):
        client = api_como(superadmin)
        client.patch(f"{BASE}/smtp/", {"password": "secreta"}, format="json")

        client.patch(f"{BASE}/smtp/", {"password": "", "host": "otro"}, format="json")

        assert ConfiguracionSMTP.actual().password == "secreta"

    def test_activa_exige_servidor_y_remitente(self, api_como, superadmin):
        response = api_como(superadmin).patch(f"{BASE}/smtp/", {"activo": True}, format="json")

        assert "host" in response.json()["error"]["detalles"]

    def test_tls_y_ssl_son_excluyentes(self, api_como, superadmin):
        response = api_como(superadmin).patch(f"{BASE}/smtp/", {"usar_tls": True, "usar_ssl": True}, format="json")

        assert "usar_ssl" in response.json()["error"]["detalles"]


class TestConexionCorreo:
    def test_sin_configuracion_activa_usa_el_entorno(self, settings):
        conexion, remitente = services.conexion_correo()

        assert remitente == settings.DEFAULT_FROM_EMAIL
        assert conexion.__class__.__module__ == "django.core.mail.backends.locmem"

    def test_con_configuracion_activa_usa_la_del_panel(self):
        ConfiguracionSMTP(
            activo=True, host="smtp.uho.edu.cu", puerto=465, usuario="sigecue", password="x",
            usar_tls=False, usar_ssl=True, remitente="SIGECUE <s@uho.edu.cu>",
        ).save()

        conexion, remitente = services.conexion_correo()

        assert remitente == "SIGECUE <s@uho.edu.cu>"
        assert (conexion.host, conexion.port, conexion.username, conexion.use_ssl) == ("smtp.uho.edu.cu", 465, "sigecue", True)

    def test_probar_envia_un_correo(self, api_como, superadmin):
        response = api_como(superadmin).post(f"{BASE}/smtp/probar/", {"destinatario": "yo@uho.edu.cu"}, format="json")

        assert response.status_code == 200
        assert mail.outbox[0].to == ["yo@uho.edu.cu"]

    def test_probar_informa_el_fallo(self, api_como, superadmin, monkeypatch):
        def falla(self, *args, **kwargs):
            raise smtplib.SMTPAuthenticationError(535, b"credenciales")

        monkeypatch.setattr("django.core.mail.EmailMessage.send", falla)

        response = api_como(superadmin).post(f"{BASE}/smtp/probar/", {"destinatario": "yo@uho.edu.cu"}, format="json")

        assert response.status_code == 400
        assert "No se pudo enviar el correo de prueba" in response.json()["error"]["mensaje"]

    def test_probar_requiere_superadmin(self, api_como, con_lectura):
        assert api_como(con_lectura).post(f"{BASE}/smtp/probar/", {"destinatario": "a@b.cu"}, format="json").status_code == 403


class TestPlantillas:
    url = f"{BASE}/plantillas/activacion_cuenta/"

    def test_lista_con_variables_disponibles(self, api_como, superadmin):
        datos = api_como(superadmin).get(f"{BASE}/plantillas/").json()

        activacion = next(p for p in datos if p["codigo"] == "activacion_cuenta")
        assert set(activacion["variables"]) == {"nombre", "enlace", "horas"}

    def test_edita_el_texto(self, api_como, superadmin):
        response = api_como(superadmin).patch(self.url, {"asunto": "Bienvenido, {{ nombre }}"}, format="json")

        assert response.status_code == 200
        assert PlantillaCorreo.objects.get(codigo="activacion_cuenta").asunto == "Bienvenido, {{ nombre }}"

    def test_rechaza_variables_desconocidas(self, api_como, superadmin):
        response = api_como(superadmin).patch(self.url, {"cuerpo": "Hola {{ nombre }} {{ ci }}"}, format="json")

        assert "ci" in response.json()["error"]["detalles"]["cuerpo"][0]

    def test_no_se_crean_ni_borran(self, api_como, superadmin):
        client = api_como(superadmin)

        assert client.post(f"{BASE}/plantillas/", {"codigo": "x"}, format="json").status_code == 405
        assert client.delete(self.url).status_code == 405

    def test_restablecer(self, api_como, superadmin):
        PlantillaCorreo.objects.filter(codigo="activacion_cuenta").update(asunto="Cambiado")

        response = api_como(superadmin).post(f"{self.url}restablecer/")

        assert response.json()["asunto"] == "SIGECUE — Activa tu cuenta"

    def test_vista_previa_con_lectura(self, api_como, con_lectura):
        response = api_como(con_lectura).post(
            f"{self.url}vista-previa/", {"asunto": "Hola {{ nombre }}", "cuerpo": "{{enlace}}"}, format="json"
        )

        assert response.json() == {"asunto": "Hola [Nombre del aspirante]", "cuerpo": "[Enlace para activar la cuenta]"}

    def test_el_correo_usa_el_texto_editado(self):
        PlantillaCorreo.objects.filter(codigo="activacion_cuenta").update(asunto="Hola {{ nombre }}", cuerpo="Ve a {{ enlace }}")

        services.enviar_correo("activacion_cuenta", ["a@b.cu"], {"nombre": "Ana", "enlace": "http://x"})

        assert (mail.outbox[0].subject, mail.outbox[0].body) == ("Hola Ana", "Ve a http://x")

    def test_sin_fila_usa_el_texto_del_catalogo(self):
        PlantillaCorreo.objects.all().delete()

        services.enviar_correo("activacion_cuenta", ["a@b.cu"], {"nombre": "Ana", "enlace": "x", "horas": 48})

        assert mail.outbox[0].subject == "SIGECUE — Activa tu cuenta"


class TestRenderizado:
    def test_sustituye_solo_variables_simples(self):
        texto = "Hola {{nombre}} y {{ nombre }}. {% include 'x' %} {{ otra }}"

        assert plantillas.renderizar(texto, {"nombre": "Ana"}) == "Hola Ana y Ana. {% include 'x' %} "

    def test_detecta_variables_desconocidas(self):
        assert plantillas.variables_desconocidas("{{ a }} {{ b }} {{ c }}", {"a": ""}) == ["b", "c"]


class TestIdentidad:
    def test_publica_sin_sesion(self, api):
        datos = api.get("/api/v1/identidad/").json()

        assert datos["color_primario"] == "#1A3A6B"
        assert datos["nombre_institucion"] == "Universidad de Holguín"

    def test_valida_colores(self, api_como, superadmin):
        response = api_como(superadmin).patch(f"{BASE}/identidad/", {"color_acento": "rojo"}, format="json")

        assert "color_acento" in response.json()["error"]["detalles"]

    def test_cambia_colores(self, api_como, superadmin):
        api_como(superadmin).patch(f"{BASE}/identidad/", {"color_acento": "#AA0000"}, format="json")

        assert IdentidadVisual.actual().color_acento == "#AA0000"
