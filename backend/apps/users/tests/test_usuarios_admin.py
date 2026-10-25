import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.nomencladores.models import Area
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


def errores(response):
    return response.json()["error"]["detalles"]


@pytest.fixture
def admin_facultad(crear_usuario, facultad):
    return crear_usuario("admin_fac", rol="admin_facultad", facultad=facultad)


@pytest.fixture
def area(facultad):
    return Area.objects.create(nombre="Área de Software", facultad=facultad)


class TestPermisos:
    def test_requiere_permiso_de_usuarios(self, api_como, crear_usuario, facultad):
        sec = crear_usuario("sec", rol="secretario_facultad", facultad=facultad)
        assert api_como(sec).get(URL).status_code == 403

    def test_lista_solo_usuarios_internos(self, api_como, superadmin, aspirante):
        nombres = [u["username"] for u in api_como(superadmin).get(URL).json()["results"]]

        assert "superadmin" in nombres
        assert aspirante.username not in nombres

    def test_rol_local_solo_ve_usuarios_de_su_entidad(self, api_como, admin_facultad, crear_usuario, otra_facultad):
        crear_usuario("ajeno", rol="secretario_facultad", facultad=otra_facultad)
        crear_usuario("jefe", rol="jefe_ci")

        nombres = [u["username"] for u in api_como(admin_facultad).get(URL).json()["results"]]

        assert nombres == ["admin_fac"]


class TestCrear:
    def test_admin_local_crea_usuario_en_su_entidad_sin_indicarla(self, api_como, admin_facultad, facultad):
        response = api_como(admin_facultad).post(URL, nuevo(), format="json")

        assert response.status_code == 201
        usuario = Usuario.objects.get(username="lrodriguez")
        assert usuario.facultad == facultad
        assert usuario.check_password(PASSWORD)
        assert response.json()["entidad"] == {"tipo": "facultad", "id": facultad.pk, "nombre": facultad.nombre}
        assert "password" not in response.json()

    def test_admin_local_no_crea_usuarios_en_otra_entidad(self, api_como, admin_facultad, otra_facultad):
        response = api_como(admin_facultad).post(URL, nuevo(facultad=otra_facultad.pk), format="json")

        assert "propia entidad" in errores(response)["facultad"][0]

    def test_admin_local_no_crea_usuarios_globales(self, api_como, admin_facultad):
        response = api_como(admin_facultad).post(URL, nuevo(rol="vicerrector"), format="json")

        assert "Superadmin" in errores(response)["rol"][0]

    def test_rol_de_facultad_exige_facultad(self, api_como, superadmin):
        assert "facultad" in errores(api_como(superadmin).post(URL, nuevo(), format="json"))

    def test_rol_de_cum_exige_cum_y_no_admite_facultad(self, api_como, superadmin, cum, facultad):
        client = api_como(superadmin)

        sin_cum = client.post(URL, nuevo(rol="secretario_cum", facultad=facultad.pk), format="json")
        con_cum = client.post(URL, nuevo(rol="secretario_cum", cum_fum=cum.pk), format="json")

        assert "cum_fum" in errores(sin_cum)
        assert con_cum.status_code == 201

    def test_rol_global_queda_sin_entidad(self, api_como, superadmin, facultad):
        response = api_como(superadmin).post(URL, nuevo(rol="vicerrector", facultad=facultad.pk), format="json")

        assert response.status_code == 201
        assert Usuario.objects.get(username="lrodriguez").facultad is None

    def test_jefe_de_area_exige_area_de_su_entidad(self, api_como, superadmin, facultad, otra_facultad, area):
        client = api_como(superadmin)
        datos = nuevo(rol="jefe_area_facultad", facultad=facultad.pk)
        area_ajena = Area.objects.create(nombre="Contabilidad", facultad=otra_facultad)

        assert "area" in errores(client.post(URL, datos, format="json"))
        assert "area" in errores(client.post(URL, datos | {"area": area_ajena.pk}, format="json"))
        assert client.post(URL, datos | {"area": area.pk}, format="json").status_code == 201
        assert Usuario.objects.get(username="lrodriguez").area == area

    def test_el_area_solo_se_guarda_si_el_rol_la_requiere(self, api_como, superadmin, facultad, area):
        api_como(superadmin).post(URL, nuevo(facultad=facultad.pk, area=area.pk), format="json")

        assert Usuario.objects.get(username="lrodriguez").area is None

    def test_asigna_cargo(self, api_como, admin_facultad):
        from apps.nomencladores.models import Cargo

        cargo = Cargo.objects.create(nombre="Profesor Titular")

        response = api_como(admin_facultad).post(URL, nuevo(cargo=cargo.pk), format="json")

        assert response.json()["cargo_nombre"] == "Profesor Titular"

    def test_no_se_asigna_el_rol_aspirante(self, api_como, superadmin):
        assert "rol" in errores(api_como(superadmin).post(URL, nuevo(rol="aspirante"), format="json"))

    def test_usuario_local_requiere_contrasena(self, api_como, admin_facultad):
        datos = nuevo()
        del datos["password"]

        assert "password" in errores(api_como(admin_facultad).post(URL, datos, format="json"))

    def test_usuario_sgu_sin_contrasena_local(self, api_como, admin_facultad):
        datos = nuevo(origen="sgu")
        del datos["password"]

        assert api_como(admin_facultad).post(URL, datos, format="json").status_code == 201
        assert not Usuario.objects.get(username="lrodriguez").has_usable_password()

    def test_usuario_sgu_no_admite_contrasena(self, api_como, admin_facultad):
        assert "password" in errores(api_como(admin_facultad).post(URL, nuevo(origen="sgu"), format="json"))

    def test_email_unico(self, api_como, admin_facultad, aspirante):
        assert "email" in errores(api_como(admin_facultad).post(URL, nuevo(email=aspirante.email), format="json"))


class TestEditar:
    def test_admin_local_no_alcanza_usuarios_globales(self, api_como, admin_facultad, crear_usuario):
        jefe = crear_usuario("jefe", rol="jefe_ci", email="jefe@uho.edu.cu")

        response = api_como(admin_facultad).patch(f"{URL}{jefe.pk}/", {"first_name": "X"}, format="json")

        assert response.status_code == 404

    def test_cambia_contrasena(self, api_como, admin_facultad, crear_usuario, facultad):
        sec = crear_usuario("sec", rol="secretario_facultad", facultad=facultad)

        api_como(admin_facultad).patch(f"{URL}{sec.pk}/", {"password": "Nueva-Clave-789"}, format="json")

        sec.refresh_from_db()
        assert sec.check_password("Nueva-Clave-789")

    def test_conserva_su_propio_email_al_editar(self, api_como, admin_facultad, crear_usuario, facultad):
        sec = crear_usuario("sec", rol="secretario_facultad", facultad=facultad, email="sec@uho.edu.cu")

        response = api_como(admin_facultad).patch(f"{URL}{sec.pk}/", {"email": "sec@uho.edu.cu"}, format="json")

        assert response.status_code == 200

    def test_cambiar_a_rol_global_quita_la_entidad(self, api_como, superadmin, crear_usuario, facultad):
        sec = crear_usuario("sec", rol="secretario_facultad", facultad=facultad)

        api_como(superadmin).patch(f"{URL}{sec.pk}/", {"rol": "vicerrector"}, format="json")

        sec.refresh_from_db()
        assert sec.facultad is None


class TestBloqueo:
    def test_bloquear_desactiva_la_cuenta(self, api_como, admin_facultad, crear_usuario, facultad):
        sec = crear_usuario("sec", rol="secretario_facultad", facultad=facultad)

        api_como(admin_facultad).post(f"{URL}{sec.pk}/bloquear/")

        sec.refresh_from_db()
        assert not sec.is_active

    def test_desbloquear_levanta_tambien_el_bloqueo_temporal(self, api_como, superadmin, crear_usuario, facultad):
        sec = crear_usuario(
            "sec", rol="secretario_facultad", facultad=facultad, is_active=False, bloqueado_hasta=timezone.now()
        )

        response = api_como(superadmin).post(f"{URL}{sec.pk}/desbloquear/")

        assert response.status_code == 200
        sec.refresh_from_db()
        assert sec.is_active and sec.bloqueado_hasta is None

    def test_no_puede_bloquearse_a_si_mismo(self, api_como, superadmin):
        assert api_como(superadmin).post(f"{URL}{superadmin.pk}/bloquear/").status_code == 400

    def test_un_rol_global_que_no_es_superadmin_no_bloquea_usuarios_globales(self, api_como, crear_usuario):
        """Un rol con usuarios.editar pero no superadmin no actúa sobre usuarios globales."""
        from apps.roles.models import Rol

        gestor = Rol.objects.create(codigo="gestor", nombre="Gestor", ambito="global")
        gestor.permisos.set(Rol.objects.get(codigo="admin_facultad").permisos.filter(modulo="usuarios"))
        jefe = crear_usuario("jefe", rol="jefe_ci")

        assert api_como(crear_usuario("g", rol=gestor)).post(f"{URL}{jefe.pk}/bloquear/").status_code == 400


class TestSinBorradoYFiltros:
    def test_los_usuarios_no_se_borran(self, api_como, superadmin, crear_usuario):
        jefe = crear_usuario("jefe", rol="jefe_ci")

        assert api_como(superadmin).delete(f"{URL}{jefe.pk}/").status_code == 405
        assert Usuario.objects.filter(pk=jefe.pk).exists()

    def test_no_existe_el_permiso_de_eliminar_usuarios(self):
        from apps.roles.models import Permiso

        assert not Permiso.objects.filter(modulo="usuarios", accion="eliminar").exists()

    def test_filtros(self, api_como, superadmin, crear_usuario, facultad):
        crear_usuario("sec", rol="secretario_facultad", facultad=facultad, first_name="Ana")
        crear_usuario("vice", rol="vicedecano", facultad=facultad, is_active=False)
        client = api_como(superadmin)

        assert client.get(URL, {"rol": "vicedecano"}).json()["count"] == 1
        assert client.get(URL, {"activo": "false"}).json()["count"] == 1
        assert client.get(URL, {"buscar": "ana"}).json()["count"] == 1


def test_la_base_de_datos_impide_dos_entidades(crear_usuario, facultad, cum):
    with pytest.raises(IntegrityError):
        crear_usuario("doble", rol="secretario_facultad", facultad=facultad, cum_fum=cum)


class TestRolesAsignables:
    url = f"{URL}roles-asignables/"

    def test_admin_local_recibe_solo_roles_de_su_ambito(self, api_como, admin_facultad):
        codigos = {r["codigo"] for r in api_como(admin_facultad).get(self.url).json()}

        assert codigos == {"admin_facultad", "vicedecano", "secretario_facultad", "jefe_area_facultad"}

    def test_superadmin_recibe_todos_menos_aspirante(self, api_como, superadmin):
        codigos = {r["codigo"] for r in api_como(superadmin).get(self.url).json()}

        assert "vicerrector" in codigos and "director_cum" in codigos
        assert "aspirante" not in codigos

    def test_no_incluye_roles_desactivados(self, api_como, superadmin):
        from apps.roles.models import Rol

        Rol.objects.filter(codigo="vicerrector").update(activo=False)

        assert "vicerrector" not in {r["codigo"] for r in api_como(superadmin).get(self.url).json()}

    def test_requiere_permiso_de_usuarios(self, api_como, crear_usuario, facultad):
        sec = crear_usuario("sec", rol="secretario_facultad", facultad=facultad)

        assert api_como(sec).get(self.url).status_code == 403
