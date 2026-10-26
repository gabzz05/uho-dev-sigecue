import smtplib

import pytest
from django.core import mail

from apps.configuracion.models import PlantillaCorreo
from apps.notificaciones import services
from apps.notificaciones.models import EnvioMasivo, Notificacion
from apps.notificaciones.tasks import enviar_correos
from apps.roles.models import Rol
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db

MIAS = "/api/v1/notificaciones/"
ENVIOS = "/api/v1/admin/notificaciones/envios/"


@pytest.fixture
def aspirante(crear_usuario):
    return crear_usuario(
        "asp", rol="aspirante", first_name="María", email="maria@nauta.cu", email_verificado=True
    )


@pytest.fixture
def jefe_ci(crear_usuario):
    return crear_usuario("jefe", rol="jefe_ci", first_name="Juan", email="jefe@uho.edu.cu")


@pytest.fixture
def admin_facultad(crear_usuario, facultad):
    return crear_usuario("admin_fac", rol="admin_facultad", facultad=facultad, email="admin@uho.edu.cu")


def notificar(usuario, n=1):
    for i in range(n):
        Notificacion.objects.create(usuario=usuario, tipo="prueba", asunto=f"Aviso {i}", cuerpo="Texto")


class TestNotificar:
    def test_crea_la_notificacion_y_envia_el_mismo_texto_por_correo(self, aspirante, django_capture_on_commit_callbacks):
        PlantillaCorreo.objects.filter(codigo="activacion_cuenta").update(asunto="Hola {{ nombre }}", cuerpo="Ir a {{ enlace }}")

        with django_capture_on_commit_callbacks(execute=True):
            services.notificar([aspirante], "activacion_cuenta", {"enlace": "http://x"})

        notificacion = Notificacion.objects.get()
        assert (notificacion.asunto, notificacion.cuerpo, notificacion.tipo) == ("Hola María", "Ir a http://x", "activacion_cuenta")
        assert (mail.outbox[0].subject, mail.outbox[0].body, mail.outbox[0].to) == ("Hola María", "Ir a http://x", ["maria@nauta.cu"])

    def test_contexto_por_destinatario(self, aspirante, jefe_ci):
        PlantillaCorreo.objects.filter(codigo="activacion_cuenta").update(cuerpo="{{ enlace }}")

        services.notificar([aspirante, jefe_ci], "activacion_cuenta", lambda u: {"enlace": u.username}, por_correo=False)

        assert sorted(Notificacion.objects.values_list("cuerpo", flat=True)) == ["asp", "jefe"]
        assert mail.outbox == []

    def test_el_correo_sigue_si_falla_un_destinatario(self, aspirante, jefe_ci, monkeypatch):
        notificar(aspirante)
        notificar(jefe_ci)
        enviados = []

        def enviar(self, *args, **kwargs):
            if self.to == ["maria@nauta.cu"]:
                raise smtplib.SMTPRecipientsRefused({})
            enviados.append(self.to)

        monkeypatch.setattr("django.core.mail.EmailMessage.send", enviar)

        assert enviar_correos(list(Notificacion.objects.values_list("pk", flat=True))) == 1
        assert enviados == [["jefe@uho.edu.cu"]]


class TestMisNotificaciones:
    def test_cada_usuario_ve_solo_las_suyas(self, api_como, aspirante, jefe_ci):
        notificar(aspirante, 2)
        notificar(jefe_ci)

        assert api_como(aspirante).get(MIAS).json()["count"] == 2

    def test_contador_de_no_leidas(self, api_como, aspirante):
        notificar(aspirante, 3)
        Notificacion.objects.filter(pk=Notificacion.objects.first().pk).update(leida=True)

        assert api_como(aspirante).get(f"{MIAS}no-leidas/").json() == {"no_leidas": 2}

    def test_resumen_recortado(self, api_como, aspirante):
        Notificacion.objects.create(usuario=aspirante, tipo="x", asunto="A", cuerpo="palabra " * 50)

        resumen = api_como(aspirante).get(MIAS).json()["results"][0]["resumen"]

        assert len(resumen) <= 140 and resumen.endswith("…")

    def test_marcar_como_leida(self, api_como, aspirante):
        notificar(aspirante)
        notificacion = Notificacion.objects.get()

        datos = api_como(aspirante).post(f"{MIAS}{notificacion.pk}/leer/").json()

        assert datos["leida"] is True and datos["leida_at"]

    def test_marcar_todas(self, api_como, aspirante):
        notificar(aspirante, 3)

        api_como(aspirante).post(f"{MIAS}leer-todas/")

        assert not Notificacion.objects.filter(leida=False).exists()

    def test_filtrar_y_borrar(self, api_como, aspirante):
        notificar(aspirante, 2)
        client = api_como(aspirante)
        primera = Notificacion.objects.first()

        assert client.delete(f"{MIAS}{primera.pk}/").status_code == 204
        assert client.get(MIAS, {"leida": "false"}).json()["count"] == 1

    def test_no_toca_las_de_otro_usuario(self, api_como, aspirante, jefe_ci):
        notificar(jefe_ci)
        ajena = Notificacion.objects.get()
        client = api_como(aspirante)

        assert client.post(f"{MIAS}{ajena.pk}/leer/").status_code == 404
        assert client.delete(f"{MIAS}{ajena.pk}/").status_code == 404

    def test_requiere_sesion(self, api):
        assert api.get(f"{MIAS}no-leidas/").status_code == 401


class TestGrupos:
    def test_todos_los_aspirantes_activos_y_verificados(self, jefe_ci, aspirante, crear_usuario):
        crear_usuario("sin_activar", rol="aspirante", email_verificado=False)
        crear_usuario("bloqueado", rol="aspirante", email_verificado=True, is_active=False)

        usuarios, descripcion, _, _ = services.resolver_grupo({"tipo": "aspirantes"}, jefe_ci)

        assert list(usuarios) == [aspirante]
        assert descripcion == "Todos los aspirantes"

    def test_rol_local_no_notifica_a_todos_los_aspirantes(self, admin_facultad):
        with pytest.raises(Exception, match="roles globales"):
            services.resolver_grupo({"tipo": "aspirantes"}, admin_facultad)

    def test_por_rol_dentro_del_ambito(self, admin_facultad, crear_usuario, facultad, otra_facultad, jefe_ci):
        propio = crear_usuario("sec1", rol="secretario_facultad", facultad=facultad)
        crear_usuario("sec2", rol="secretario_facultad", facultad=otra_facultad)

        local, _, _, _ = services.resolver_grupo({"tipo": "rol", "rol": "secretario_facultad"}, admin_facultad)
        todos, _, _, _ = services.resolver_grupo({"tipo": "rol", "rol": "secretario_facultad"}, jefe_ci)

        assert list(local) == [propio]
        assert todos.count() == 2

    def test_por_entidad(self, jefe_ci, admin_facultad, crear_usuario, facultad, cum):
        crear_usuario("sec", rol="secretario_facultad", facultad=facultad)
        crear_usuario("dir", rol="director_cum", cum_fum=cum)

        de_facultad, _, _, _ = services.resolver_grupo({"tipo": "entidad", "facultad": facultad.pk}, jefe_ci)
        propia, _, _, _ = services.resolver_grupo({"tipo": "entidad", "cum_fum": cum.pk}, admin_facultad)

        assert de_facultad.count() == 2  # admin_fac y sec
        assert set(propia.values_list("username", flat=True)) == {"admin_fac", "sec"}  # ignora la entidad pedida

    def test_global_debe_indicar_una_entidad(self, jefe_ci):
        with pytest.raises(Exception, match="Facultad o un CUM"):
            services.resolver_grupo({"tipo": "entidad"}, jefe_ci)


class TestEnviosMasivos:
    def test_envia_registra_y_personaliza(self, api_como, jefe_ci, aspirante, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            response = api_como(jefe_ci).post(
                ENVIOS,
                {"grupo": {"tipo": "aspirantes"}, "asunto": "Aviso", "cuerpo": "Hola {{ nombre }}", "por_correo": True},
                format="json",
            )

        assert response.status_code == 201
        assert response.json()["destinatarios"] == 1
        assert Notificacion.objects.get(usuario=aspirante).cuerpo == "Hola María"
        assert mail.outbox[0].body == "Hola María"
        assert EnvioMasivo.objects.get().enviado_por == jefe_ci

    def test_sin_correo_por_defecto(self, api_como, jefe_ci, aspirante, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            api_como(jefe_ci).post(ENVIOS, {"grupo": {"tipo": "aspirantes"}, "asunto": "A", "cuerpo": "B"}, format="json")

        assert mail.outbox == []
        assert Notificacion.objects.count() == 1

    def test_solo_admite_la_variable_nombre(self, api_como, jefe_ci, aspirante):
        response = api_como(jefe_ci).post(
            ENVIOS, {"grupo": {"tipo": "aspirantes"}, "asunto": "A", "cuerpo": "{{ ci }}"}, format="json"
        )

        assert response.status_code == 400
        assert "ci" in response.json()["error"]["mensaje"]

    def test_grupo_vacio(self, api_como, jefe_ci):
        response = api_como(jefe_ci).post(ENVIOS, {"grupo": {"tipo": "aspirantes"}, "asunto": "A", "cuerpo": "B"}, format="json")

        assert "no tiene destinatarios" in response.json()["error"]["mensaje"]

    def test_contar_destinatarios(self, api_como, jefe_ci, aspirante):
        datos = api_como(jefe_ci).post(f"{ENVIOS}contar/", {"tipo": "aspirantes"}, format="json").json()

        assert datos == {"destinatarios": 1, "descripcion": "Todos los aspirantes"}

    def test_requiere_permiso_de_crear(self, api_como, crear_usuario, facultad):
        sec = crear_usuario("sec", rol="secretario_facultad", facultad=facultad)

        response = api_como(sec).post(ENVIOS, {"grupo": {"tipo": "entidad"}, "asunto": "A", "cuerpo": "B"}, format="json")

        assert response.status_code == 403

    def test_historial_por_ambito(self, api_como, jefe_ci, admin_facultad, crear_usuario, facultad):
        crear_usuario("sec", rol="secretario_facultad", facultad=facultad)
        api_como(admin_facultad).post(ENVIOS, {"grupo": {"tipo": "entidad"}, "asunto": "Local", "cuerpo": "B"}, format="json")
        services.enviar_masivo(jefe_ci, {"tipo": "rol", "rol": "secretario_facultad"}, "Global", "B")

        locales = [e["asunto"] for e in api_como(admin_facultad).get(ENVIOS).json()["results"]]
        globales = [e["asunto"] for e in api_como(jefe_ci).get(ENVIOS).json()["results"]]

        assert locales == ["Local"]
        assert set(globales) == {"Local", "Global"}


def test_los_aspirantes_pueden_ver_sus_notificaciones(api_como, aspirante):
    assert Rol.objects.get(codigo="aspirante").permisos.count() == 0
    assert api_como(aspirante).get(MIAS).status_code == 200


def test_borrar_el_usuario_borra_sus_notificaciones(aspirante):
    notificar(aspirante)
    Usuario.objects.filter(pk=aspirante.pk).delete()

    assert not Notificacion.objects.exists()
