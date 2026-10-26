from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import path
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.test import APIClient

from apps.auditoria import services
from apps.auditoria.models import LogAuditoria, LogInmutableError


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def _recurso(request, pk=None):
    if request.data.get("fallar"):
        return Response({}, status=400)
    return Response({})


urlpatterns = [
    path("api/v1/carreras/", _recurso),
    path("api/v1/admin/plan-plazas/<int:pk>/", _recurso),
]

pytestmark = pytest.mark.django_db


@pytest.fixture
def usuario():
    return get_user_model().objects.create_user("jcastro", password="x")


@pytest.fixture
def admin():
    return get_user_model().objects.create_superuser("admin", password="x")


def _log(**kwargs):
    datos = {"accion": "prueba", "modulo": "test"} | kwargs
    return services.registrar(**datos)


class TestInmutabilidad:
    def test_no_se_puede_modificar(self):
        log = _log()
        log.accion = "otra"
        with pytest.raises(LogInmutableError):
            log.save()

    def test_no_se_puede_borrar(self):
        with pytest.raises(LogInmutableError):
            _log().delete()

    def test_no_se_puede_modificar_ni_borrar_en_bloque(self):
        _log()
        with pytest.raises(LogInmutableError):
            LogAuditoria.objects.update(accion="x")
        with pytest.raises(LogInmutableError):
            LogAuditoria.objects.all().delete()


class TestRegistrar:
    def test_guarda_usuario_ip_y_ruta(self, usuario):
        request = RequestFactory().post("/api/v1/carreras/", REMOTE_ADDR="10.0.0.5")
        request.user = usuario

        log = services.registrar(request=request, accion="crear", modulo="carreras")

        assert log.usuario == usuario
        assert log.usuario_nombre == "jcastro"
        assert log.ip == "10.0.0.5"
        assert log.metodo == "POST"
        assert log.ruta == "/api/v1/carreras/"

    def test_usuario_anonimo_queda_vacio(self):
        from django.contrib.auth.models import AnonymousUser

        request = RequestFactory().get("/")
        request.user = AnonymousUser()

        log = services.registrar(request=request, accion="x", modulo="y")

        assert log.usuario is None
        assert log.usuario_nombre == ""

    def test_x_forwarded_for_solo_si_se_confia_en_el_proxy(self, settings):
        request = RequestFactory().get("/", HTTP_X_FORWARDED_FOR="200.1.1.1, 10.0.0.1", REMOTE_ADDR="10.0.0.1")

        settings.AUDITORIA_CONFIAR_X_FORWARDED_FOR = False
        assert services.obtener_ip(request) == "10.0.0.1"
        settings.AUDITORIA_CONFIAR_X_FORWARDED_FOR = True
        assert services.obtener_ip(request) == "200.1.1.1"

    def test_un_fallo_al_auditar_no_rompe_la_operacion(self, monkeypatch):
        def falla(**kwargs):
            raise RuntimeError("db caida")

        monkeypatch.setattr(LogAuditoria.objects, "create", falla)
        assert _log() is None


@pytest.mark.urls(__name__)
class TestMiddleware:
    def test_registra_peticiones_que_modifican_datos(self):
        APIClient().post("/api/v1/carreras/", {}, format="json")

        log = LogAuditoria.objects.get()
        assert log.accion == "POST api/v1/carreras/"
        assert log.modulo == "carreras"
        assert log.resultado == LogAuditoria.Resultado.EXITO
        assert log.codigo_http == 200

    def test_registra_errores(self):
        APIClient().post("/api/v1/carreras/", {"fallar": True}, format="json")

        assert LogAuditoria.objects.get().resultado == LogAuditoria.Resultado.ERROR

    def test_modulo_y_entidad_en_rutas_de_admin(self):
        APIClient().post("/api/v1/admin/plan-plazas/7/", {}, format="json")

        log = LogAuditoria.objects.get()
        assert log.modulo == "plan-plazas"
        assert log.entidad_id == "7"

    def test_no_registra_lecturas(self):
        APIClient().get("/api/v1/carreras/")

        assert not LogAuditoria.objects.exists()

    def test_registra_el_usuario_autenticado_por_drf(self, usuario):
        client = APIClient()
        client.force_authenticate(usuario)
        client.post("/api/v1/carreras/", {}, format="json")

        assert LogAuditoria.objects.get().usuario == usuario


class TestConsulta:
    url = "/api/v1/admin/logs/"

    def test_requiere_permiso(self, usuario):
        client = APIClient()
        client.force_authenticate(usuario)

        assert client.get(self.url).status_code == 403

    def test_lista_y_filtra(self, admin, usuario):
        _log(accion="otorgar plaza", modulo="otorgamiento", usuario=usuario)
        _log(accion="crear carrera", modulo="carreras", resultado=LogAuditoria.Resultado.ERROR)
        client = APIClient()
        client.force_authenticate(admin)

        assert client.get(self.url).json()["count"] == 2
        assert client.get(self.url, {"modulo": "carreras"}).json()["count"] == 1
        assert client.get(self.url, {"accion": "otorgar"}).json()["count"] == 1
        assert client.get(self.url, {"usuario": usuario.pk}).json()["count"] == 1
        assert client.get(self.url, {"resultado": "error"}).json()["count"] == 1

    def test_filtra_por_fechas(self, admin):
        _log()
        client = APIClient()
        client.force_authenticate(admin)
        hoy = timezone.localdate()

        assert client.get(self.url, {"desde": hoy.isoformat()}).json()["count"] == 1
        assert client.get(self.url, {"hasta": (hoy - timedelta(days=1)).isoformat()}).json()["count"] == 0

    def test_filtra_por_nombre_de_usuario(self, admin, usuario):
        _log(usuario=usuario)
        _log()
        client = APIClient()
        client.force_authenticate(admin)

        assert client.get(self.url, {"usuario_nombre": "CASTRO"}).json()["count"] == 1

    def test_lista_los_modulos_registrados(self, admin):
        _log(modulo="usuarios")
        _log(modulo="auth")
        _log(modulo="usuarios")
        client = APIClient()
        client.force_authenticate(admin)

        assert client.get(f"{self.url}modulos/").json() == {"modulos": ["auth", "usuarios"]}

    def test_es_solo_lectura(self, admin):
        client = APIClient()
        client.force_authenticate(admin)

        assert client.post(self.url, {}).status_code == 405
