import pytest

from apps.users.models import Usuario

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/usuarios/"


def nuevo(**extra):
    return {
        "username": "lrodriguez",
        "first_name": "Luis",
        "last_name": "Rodríguez",
        "email": "luis@uho.edu.cu",
        "rol": "secretario_facultad",
        "password": PASSWORD,
    } | extra


@pytest.fixture
def admin_facultad(crear_usuario):
    return crear_usuario("admin_fac", rol="admin_facultad")


class TestPermisos:
    def test_requiere_permiso_de_usuarios(self, api_como, crear_usuario):
        assert api_como(crear_usuario("sec", rol="secretario_facultad")).get(URL).status_code == 403

    def test_lista_solo_usuarios_internos(self, api_como, admin_facultad, aspirante):
        nombres = [u["username"] for u in api_como(admin_facultad).get(URL).json()["results"]]

        assert "admin_fac" in nombres
        assert aspirante.username not in nombres


class TestCrear:
    def test_admin_local_crea_usuario_con_rol_local(self, api_como, admin_facultad):
        response = api_como(admin_facultad).post(URL, nuevo(), format="json")

        assert response.status_code == 201
        usuario = Usuario.objects.get(username="lrodriguez")
        assert usuario.check_password(PASSWORD)
        assert usuario.email == "luis@uho.edu.cu"
        assert "password" not in response.json()

    def test_admin_local_no_crea_usuarios_globales(self, api_como, admin_facultad):
        response = api_como(admin_facultad).post(URL, nuevo(rol="vicerrector"), format="json")

        assert response.status_code == 400
        assert "Superadmin" in response.json()["error"]["detalles"]["rol"][0]

    def test_superadmin_crea_usuarios_globales(self, api_como, superadmin):
        assert api_como(superadmin).post(URL, nuevo(rol="vicerrector"), format="json").status_code == 201

    def test_no_se_asigna_el_rol_aspirante(self, api_como, superadmin):
        response = api_como(superadmin).post(URL, nuevo(rol="aspirante"), format="json")

        assert "rol" in response.json()["error"]["detalles"]

    def test_usuario_local_requiere_contrasena(self, api_como, superadmin):
        datos = nuevo()
        del datos["password"]

        assert "password" in api_como(superadmin).post(URL, datos, format="json").json()["error"]["detalles"]

    def test_usuario_sgu_sin_contrasena_local(self, api_como, superadmin):
        datos = nuevo(origen="sgu")
        del datos["password"]

        assert api_como(superadmin).post(URL, datos, format="json").status_code == 201
        assert not Usuario.objects.get(username="lrodriguez").has_usable_password()

    def test_usuario_sgu_no_admite_contrasena(self, api_como, superadmin):
        response = api_como(superadmin).post(URL, nuevo(origen="sgu"), format="json")

        assert "password" in response.json()["error"]["detalles"]

    def test_email_unico(self, api_como, superadmin, aspirante):
        response = api_como(superadmin).post(URL, nuevo(email=aspirante.email), format="json")

        assert "email" in response.json()["error"]["detalles"]


class TestEditar:
    def test_admin_local_no_edita_usuarios_globales(self, api_como, admin_facultad, crear_usuario):
        jefe = crear_usuario("jefe", rol="jefe_ci", email="jefe@uho.edu.cu")

        response = api_como(admin_facultad).patch(f"{URL}{jefe.pk}/", {"first_name": "X"}, format="json")

        assert response.status_code == 400

    def test_cambia_contrasena(self, api_como, superadmin, crear_usuario):
        sec = crear_usuario("sec", rol="secretario_facultad")

        api_como(superadmin).patch(f"{URL}{sec.pk}/", {"password": "Nueva-Clave-789"}, format="json")

        sec.refresh_from_db()
        assert sec.check_password("Nueva-Clave-789")

    def test_conserva_su_propio_email_al_editar(self, api_como, superadmin, crear_usuario):
        sec = crear_usuario("sec", rol="secretario_facultad", email="sec@uho.edu.cu")

        response = api_como(superadmin).patch(f"{URL}{sec.pk}/", {"email": "sec@uho.edu.cu"}, format="json")

        assert response.status_code == 200


class TestBloqueo:
    def test_bloquear_impide_iniciar_sesion(self, api, api_como, superadmin, crear_usuario):
        sec = crear_usuario("sec", rol="secretario_facultad")

        api_como(superadmin).post(f"{URL}{sec.pk}/bloquear/")

        sec.refresh_from_db()
        assert not sec.is_active

    def test_desbloquear_levanta_tambien_el_bloqueo_temporal(self, api_como, superadmin, crear_usuario):
        from django.utils import timezone

        sec = crear_usuario("sec", rol="secretario_facultad", is_active=False, bloqueado_hasta=timezone.now())

        response = api_como(superadmin).post(f"{URL}{sec.pk}/desbloquear/")

        assert response.status_code == 200
        sec.refresh_from_db()
        assert sec.is_active and sec.bloqueado_hasta is None

    def test_no_puede_bloquearse_a_si_mismo(self, api_como, superadmin):
        assert api_como(superadmin).post(f"{URL}{superadmin.pk}/bloquear/").status_code == 400

    def test_admin_local_no_bloquea_usuarios_globales(self, api_como, admin_facultad, crear_usuario):
        jefe = crear_usuario("jefe", rol="jefe_ci")

        assert api_como(admin_facultad).post(f"{URL}{jefe.pk}/bloquear/").status_code == 400


class TestEliminarYFiltrar:
    def test_elimina_usuario(self, api_como, superadmin, crear_usuario):
        sec = crear_usuario("sec", rol="secretario_facultad")

        assert api_como(superadmin).delete(f"{URL}{sec.pk}/").status_code == 204
        assert not Usuario.objects.filter(pk=sec.pk).exists()

    def test_no_se_elimina_a_si_mismo(self, api_como, superadmin):
        assert api_como(superadmin).delete(f"{URL}{superadmin.pk}/").status_code == 400

    def test_filtros(self, api_como, superadmin, crear_usuario):
        crear_usuario("sec", rol="secretario_facultad", first_name="Ana")
        crear_usuario("vice", rol="vicedecano", is_active=False)
        client = api_como(superadmin)

        assert client.get(URL, {"rol": "vicedecano"}).json()["count"] == 1
        assert client.get(URL, {"activo": "false"}).json()["count"] == 1
        assert client.get(URL, {"buscar": "ana"}).json()["count"] == 1
