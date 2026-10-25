import pytest
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.roles.catalogo import MODULOS
from apps.roles.models import Permiso, Rol
from apps.roles.permissions import PermisoModulo

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/roles/"


class TestDatosIniciales:
    def test_existen_los_13_roles_de_la_ers(self):
        assert Rol.objects.filter(es_sistema=True).count() == 13

    def test_permisos_en_bd_coinciden_con_el_catalogo(self):
        esperados = {f"{m}.{a}" for m, (_, acciones) in MODULOS.items() for a in acciones}
        assert {p.codigo for p in Permiso.objects.all()} == esperados

    def test_solo_superadmin_y_jefe_ci_ven_logs(self, crear_usuario):
        con_logs = {
            r.codigo for r in Rol.objects.all() if crear_usuario(r.codigo, rol=r).tiene_permiso("logs", "ver")
        }
        assert con_logs == {"superadmin", "jefe_ci"}

    def test_aspirante_no_tiene_permisos_administrativos(self):
        assert not Rol.objects.get(codigo="aspirante").permisos.exists()


class TestTienePermiso:
    def test_segun_permisos_del_rol(self, crear_usuario):
        secretario = crear_usuario(rol="secretario_facultad")

        assert secretario.tiene_permiso("solicitudes", "editar")
        assert not secretario.tiene_permiso("usuarios", "crear")

    def test_superadmin_tiene_todo(self, superadmin):
        assert superadmin.tiene_permiso("cualquier_modulo", "cualquier_accion")

    def test_usuario_inactivo_no_tiene_permisos(self, crear_usuario):
        assert not crear_usuario(rol="jefe_ci", is_active=False).tiene_permiso("dashboard", "ver")

    def test_rol_desactivado_pierde_permisos(self, crear_usuario):
        Rol.objects.filter(codigo="jefe_ci").update(activo=False)
        assert not crear_usuario(rol="jefe_ci").tiene_permiso("dashboard", "ver")

    def test_sin_rol_no_tiene_permisos(self, crear_usuario):
        assert not crear_usuario().tiene_permiso("dashboard", "ver")


class TestPermisoModulo:
    class _Vista(APIView):
        modulo = "solicitudes"
        acciones_permiso = {"aprobar": "editar"}

    def _permite(self, usuario, accion):
        request = APIRequestFactory().get("/")
        request.user = usuario
        vista = self._Vista()
        vista.action = accion
        return PermisoModulo().has_permission(request, vista)

    def test_traduce_acciones_estandar(self, crear_usuario):
        jefe_area = crear_usuario(rol="jefe_area_facultad")

        assert self._permite(jefe_area, "list")
        assert not self._permite(jefe_area, "partial_update")

    def test_acciones_propias_declaradas(self, crear_usuario):
        assert self._permite(crear_usuario(rol="secretario_facultad"), "aprobar")

    def test_accion_no_declarada_se_deniega(self, superadmin):
        assert not self._permite(superadmin, "accion_desconocida")

    def test_anonimo_se_deniega(self):
        from django.contrib.auth.models import AnonymousUser

        assert not self._permite(AnonymousUser(), "list")


class TestApiRoles:
    def test_requiere_permiso_de_roles(self, api_como, crear_usuario):
        assert api_como(crear_usuario(rol="jefe_ci")).get(URL).status_code == 403

    def test_superadmin_lista_roles(self, api_como, superadmin):
        response = api_como(superadmin).get(URL)

        assert response.status_code == 200
        assert response.json()["count"] == 13

    def test_crear_rol_con_permisos(self, api_como, superadmin):
        response = api_como(superadmin).post(
            URL,
            {"codigo": "auditor", "nombre": "Auditor", "ambito": "global", "permisos": ["logs.ver", "dashboard.ver"]},
            format="json",
        )

        assert response.status_code == 201
        assert response.json()["permisos"] == ["dashboard.ver", "logs.ver"]
        assert response.json()["es_sistema"] is False

    def test_rechaza_permisos_inexistentes(self, api_como, superadmin):
        response = api_como(superadmin).post(
            URL, {"codigo": "x", "nombre": "X", "ambito": "global", "permisos": ["nada.ver"]}, format="json"
        )

        assert response.status_code == 400
        assert "permisos" in response.json()["error"]["detalles"]

    def test_editar_permisos_de_rol_del_sistema(self, api_como, superadmin):
        rol = Rol.objects.get(codigo="jefe_area_facultad")

        response = api_como(superadmin).patch(f"{URL}{rol.pk}/", {"permisos": ["dashboard.ver"]}, format="json")

        assert response.status_code == 200
        assert response.json()["permisos"] == ["dashboard.ver"]

    def test_no_cambia_codigo_ni_ambito_de_rol_del_sistema(self, api_como, superadmin):
        rol = Rol.objects.get(codigo="vicerrector")
        client = api_como(superadmin)

        assert client.patch(f"{URL}{rol.pk}/", {"codigo": "otro"}, format="json").status_code == 400
        assert client.patch(f"{URL}{rol.pk}/", {"ambito": "facultad"}, format="json").status_code == 400

    def test_no_elimina_rol_del_sistema(self, api_como, superadmin):
        rol = Rol.objects.get(codigo="vicerrector")

        response = api_como(superadmin).delete(f"{URL}{rol.pk}/")

        assert response.status_code == 400
        assert Rol.objects.filter(pk=rol.pk).exists()

    def test_no_elimina_rol_con_usuarios(self, api_como, superadmin, crear_usuario):
        rol = Rol.objects.create(codigo="temporal", nombre="Temporal", ambito="global")
        crear_usuario("alguien", rol=rol)

        assert api_como(superadmin).delete(f"{URL}{rol.pk}/").status_code == 400

    def test_elimina_rol_propio_sin_usuarios(self, api_como, superadmin):
        rol = Rol.objects.create(codigo="temporal", nombre="Temporal", ambito="global")

        assert api_como(superadmin).delete(f"{URL}{rol.pk}/").status_code == 204

    def test_catalogo_agrupado_por_modulo(self, api_como, superadmin):
        datos = api_como(superadmin).get(f"{URL}catalogo/").json()

        logs = next(m for m in datos if m["modulo"] == "logs")
        assert logs["acciones"] == [{"codigo": "logs.ver", "accion": "ver", "nombre": "Ver"}]
