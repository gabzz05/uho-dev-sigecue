from datetime import timedelta

import pytest
from django.utils import timezone

from apps.auditoria.models import LogAuditoria
from apps.users import sgu
from apps.users.models import Usuario

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login/"
REFRESH = "/api/v1/auth/refresh/"
LOGOUT = "/api/v1/auth/logout/"
ME = "/api/v1/auth/me/"
COOKIE = "sigecue_refresh"


def login(api, identificador, password=PASSWORD):
    return api.post(LOGIN, {"identificador": identificador, "password": password}, format="json")


class TestLogin:
    def test_aspirante_entra_con_su_email(self, api, aspirante):
        response = login(api, "Maria@Nauta.cu")

        assert response.status_code == 200
        assert response.json()["usuario"]["email"] == "maria@nauta.cu"
        assert response.json()["access"]

    def test_interno_entra_con_su_usuario(self, api, crear_usuario):
        crear_usuario("jcastro", rol="jefe_ci")

        response = login(api, "jcastro")

        assert response.status_code == 200
        assert response.json()["usuario"]["rol"]["codigo"] == "jefe_ci"

    def test_access_token_permite_usar_la_api(self, api, aspirante):
        access = login(api, "maria@nauta.cu").json()["access"]
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        assert api.get(ME).status_code == 200

    def test_refresh_va_en_cookie_httponly_y_no_en_el_cuerpo(self, api, aspirante):
        response = login(api, "maria@nauta.cu")

        cookie = response.cookies[COOKIE]
        assert cookie["httponly"]
        assert cookie["path"] == "/api/v1/auth/"
        assert cookie["samesite"] == "Strict"
        assert "refresh" not in response.json()

    def test_password_incorrecta_y_usuario_inexistente_dan_el_mismo_mensaje(self, api, aspirante):
        mal_password = login(api, "maria@nauta.cu", "otra")
        inexistente = login(api, "nadie@nauta.cu")

        assert mal_password.status_code == inexistente.status_code == 401
        assert mal_password.json() == inexistente.json()

    def test_cuenta_bloqueada_por_admin(self, api, aspirante):
        aspirante.is_active = False
        aspirante.save()

        response = login(api, "maria@nauta.cu")

        assert response.status_code == 403
        assert "bloqueada" in response.json()["error"]["mensaje"]

    def test_aspirante_sin_activar_no_entra(self, api, aspirante):
        aspirante.email_verificado = False
        aspirante.save()

        response = login(api, "maria@nauta.cu")

        assert response.status_code == 403
        assert "activar" in response.json()["error"]["mensaje"]

    def test_queda_auditado_con_el_usuario(self, api, aspirante):
        login(api, "maria@nauta.cu")

        log = LogAuditoria.objects.get(modulo="auth")
        assert log.usuario == aspirante
        assert log.resultado == "exito"


class TestBloqueoTemporal:
    def test_se_bloquea_tras_5_intentos_fallidos(self, api, aspirante):
        for _ in range(5):
            login(api, "maria@nauta.cu", "mal")

        response = login(api, "maria@nauta.cu")

        assert response.status_code == 403
        assert "intentos fallidos" in response.json()["error"]["mensaje"]
        aspirante.refresh_from_db()
        assert aspirante.bloqueado_hasta > timezone.now() + timedelta(minutes=14)

    def test_el_bloqueo_se_audita(self, api, aspirante):
        for _ in range(5):
            login(api, "maria@nauta.cu", "mal")

        assert LogAuditoria.objects.filter(accion__startswith="bloqueo temporal", usuario=aspirante).exists()

    def test_un_acierto_reinicia_el_contador(self, api, aspirante):
        for _ in range(4):
            login(api, "maria@nauta.cu", "mal")
        login(api, "maria@nauta.cu")

        aspirante.refresh_from_db()
        assert aspirante.intentos_fallidos == 0

    def test_pasado_el_bloqueo_puede_entrar(self, api, aspirante):
        aspirante.bloqueado_hasta = timezone.now() - timedelta(seconds=1)
        aspirante.save()

        assert login(api, "maria@nauta.cu").status_code == 200

    def test_parametros_configurables_desde_el_panel(self, api, aspirante):
        from apps.configuracion.models import ConfiguracionSistema

        ConfiguracionSistema.objects.update_or_create(pk=1, defaults={"login_max_intentos": 2, "login_bloqueo_minutos": 60})
        login(api, "maria@nauta.cu", "mal")
        login(api, "maria@nauta.cu", "mal")

        assert login(api, "maria@nauta.cu").status_code == 403
        aspirante.refresh_from_db()
        assert aspirante.bloqueado_hasta > timezone.now() + timedelta(minutes=59)


class TestRefreshYLogout:
    def test_refresh_con_cookie_devuelve_access_y_rota_la_cookie(self, api, aspirante):
        original = login(api, "maria@nauta.cu").cookies[COOKIE].value

        response = api.post(REFRESH)

        assert response.status_code == 200
        assert response.json()["access"]
        assert response.cookies[COOKIE].value != original

    def test_refresh_sin_cookie_es_401(self, api):
        response = api.post(REFRESH)

        assert response.status_code == 401
        assert response.json()["error"]["codigo"] == "sesion_expirada"

    def test_un_refresh_rotado_no_se_puede_reutilizar(self, api, aspirante):
        original = login(api, "maria@nauta.cu").cookies[COOKIE].value
        api.post(REFRESH)
        api.cookies[COOKIE] = original

        assert api.post(REFRESH).status_code == 401

    def test_logout_invalida_el_refresh(self, api, aspirante):
        refresh = login(api, "maria@nauta.cu").cookies[COOKIE].value

        response = api.post(LOGOUT)
        api.cookies[COOKIE] = refresh

        assert response.status_code == 204
        assert api.post(REFRESH).status_code == 401

    def test_logout_sin_sesion_no_falla(self, api):
        assert api.post(LOGOUT).status_code == 204


class _SGUDePrueba(sgu.ProveedorSGU):
    def autenticar(self, username, password):
        return sgu.IdentidadSGU(username=username) if password == "clave-sgu" else None


class TestSGU:
    def test_sin_proveedor_configurado_el_usuario_sgu_no_entra(self, api, crear_usuario):
        crear_usuario("profe", rol="secretario_facultad", origen=Usuario.Origen.SGU)

        assert login(api, "profe", "clave-sgu").status_code == 401

    def test_con_proveedor_valida_contra_el_sgu(self, api, crear_usuario, settings):
        settings.SGU_PROVEEDOR = f"{__name__}._SGUDePrueba"
        crear_usuario("profe", rol="secretario_facultad", origen=Usuario.Origen.SGU)

        assert login(api, "profe", "clave-sgu").status_code == 200
        assert login(api, "profe", PASSWORD).status_code == 401

    def test_el_contrato_base_no_esta_implementado(self):
        with pytest.raises(NotImplementedError):
            sgu.ProveedorSGU().autenticar("x", "y")
