from datetime import timedelta

import pytest
from django.core.files.storage import default_storage
from django.utils import timezone

from apps.aspirantes.models import DocumentoAspirante, PerfilAspirante, TipoDocumento
from apps.auditoria.models import LogAuditoria
from apps.interes.models import ConvocatoriaInteres, ExpresionInteres
from apps.notificaciones.models import Notificacion
from apps.otorgamiento import services as otorgamiento
from apps.otorgamiento.models import ResultadoOtorgamiento
from apps.otorgamiento.tests.test_otorgamiento import escenario, usuarios  # noqa: F401 (fixtures)
from apps.otorgamiento.tests.test_otorgamiento import otorgamiento as generado  # noqa: F401
from apps.retencion import services
from apps.retencion.models import RetencionEjecutada
from apps.retencion.services import sumar_anios
from apps.solicitudes.models import Solicitud
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db

HOY = timezone.localdate()


@pytest.fixture
def publicado(usuarios, generado, escenario, django_capture_on_commit_callbacks):  # noqa: F811
    with django_capture_on_commit_callbacks(execute=True):
        otorgamiento.aprobar(usuarios["jefe"], generado)
        otorgamiento.publicar(usuarios["vicerrector"], generado, segunda_convocatoria=False)
    return generado


def aspirante(escenario, nombre):  # noqa: F811
    return Usuario.objects.get(pk=escenario[nombre].aspirante_id)


def en(anios, dias=1):
    return sumar_anios(HOY, anios) + timedelta(days=dias)


class TestPlazos:
    def test_hoy_no_hay_nada_que_anonimizar(self, publicado):
        assert services.previsualizar()["aspirantes"] == 0

    def test_a_los_2_anios_los_no_seleccionados_y_las_versiones_antiguas(self, publicado, escenario):  # noqa: F811
        ana = aspirante(escenario, "ana")
        DocumentoAspirante.objects.filter(perfil__usuario=ana, tipo__nombre="CI anverso").update(vigente=False)
        DocumentoAspirante.objects.create(
            perfil=PerfilAspirante.objects.get(usuario=ana), tipo=TipoDocumento.objects.get(nombre="CI anverso"), version=2,
            archivo="x.pdf", nombre_original="x.pdf", formato="PDF", tamano=10,
        )

        vista = services.previsualizar(hoy=en(2))

        assert (vista["aspirantes"], vista["solo_versiones_antiguas"]) == (1, 3)  # Pepe; Ana, Luis y Eva conservan lo vigente
        services.ejecutar(hoy=en(2))
        assert aspirante(escenario, "pepe").anonimizado_at is not None
        assert aspirante(escenario, "ana").anonimizado_at is None
        assert not DocumentoAspirante.objects.filter(perfil__usuario=ana, vigente=False).exists()
        assert DocumentoAspirante.objects.filter(perfil__usuario=ana, vigente=True).count() == 3

    def test_los_otorgados_a_los_5_anios(self, publicado, escenario):  # noqa: F811
        assert services.previsualizar(hoy=en(5, dias=-2))["aspirantes"] == 1

        services.ejecutar(hoy=en(5))

        assert Usuario.objects.filter(anonimizado_at__isnull=False).count() == 4

    def test_los_plazos_son_configurables(self, publicado):
        from apps.configuracion.models import ConfiguracionSistema

        ConfiguracionSistema.objects.update(retencion_anios=1)

        assert services.previsualizar(hoy=en(1))["aspirantes"] == 1

    def test_una_solicitud_posterior_aplaza_la_anonimizacion(self, publicado, escenario, ofertas):  # noqa: F811
        from apps.convocatorias.models import ConvocatoriaSolicitud

        siguiente = ConvocatoriaSolicitud.objects.create(anio_academico="2027-2028", fecha_inicio=HOY, fecha_cierre=HOY, estado="cerrada")
        Solicitud.objects.create(aspirante=aspirante(escenario, "pepe"), convocatoria=siguiente, estado=Solicitud.Estado.PENDIENTE)

        assert services.previsualizar(hoy=en(2))["aspirantes"] == 0

    def test_sin_solicitud_cuenta_desde_el_ultimo_acceso(self, crear_aspirante):
        nunca = crear_aspirante("asp_nunca", ci="91010112345", email="nunca@nauta.cu")
        Usuario.objects.filter(pk=nunca.pk).update(date_joined=timezone.now() - timedelta(days=800), last_login=None)

        assert services.previsualizar()["aspirantes"] == 1


class TestAnonimizacion:
    def test_quita_los_datos_personales_y_conserva_el_proceso(self, publicado, escenario, django_capture_on_commit_callbacks):  # noqa: F811
        pepe = aspirante(escenario, "pepe")
        archivos = list(DocumentoAspirante.objects.filter(perfil__usuario=pepe).values_list("archivo", flat=True)) + [pepe.foto.name]
        assert Notificacion.objects.filter(usuario=pepe).exists()
        log = LogAuditoria.objects.create(usuario=pepe, usuario_nombre=pepe.username, accion="x", modulo="y", resultado="exito")

        with django_capture_on_commit_callbacks(execute=True):
            ejecucion = services.ejecutar(hoy=en(2))

        pepe.refresh_from_db()
        assert pepe.nombre_completo == "Aspirante anonimizado"
        assert "anon_" in pepe.username and "pepe" not in pepe.username
        assert (pepe.ci, pepe.email, pepe.celular, pepe.ci_hash, pepe.email_hash) == ("", "", "", None, None)
        assert (pepe.is_active, pepe.has_usable_password(), bool(pepe.foto)) == (False, False, False)
        assert PerfilAspirante.objects.get(usuario=pepe).centro_trabajo == ""
        assert PerfilAspirante.objects.get(usuario=pepe).indice_validado is not None
        assert not DocumentoAspirante.objects.filter(perfil__usuario=pepe).exists()
        assert not any(default_storage.exists(nombre) for nombre in archivos)
        assert not Notificacion.objects.filter(usuario=pepe).exists()
        # Se conservan solicitud, carreras, estado y snapshot del otorgamiento.
        solicitud = Solicitud.objects.get(aspirante=pepe)
        assert (solicitud.estado, solicitud.carreras.count()) == ("no_seleccionado", 1)
        assert ResultadoOtorgamiento.objects.get(aspirante=pepe).aspirante_nombre == "Aspirante anonimizado"
        # La auditoría no se toca.
        log.refresh_from_db()
        assert log.usuario_id == pepe.pk
        assert (ejecucion.aspirantes_anonimizados, ejecucion.documentos_eliminados) == (1, 4)  # 3 documentos + foto

    def test_ejecutar_dos_veces_no_repite(self, publicado):
        services.ejecutar(hoy=en(2))
        segunda = services.ejecutar(hoy=en(2))

        assert (segunda.aspirantes_anonimizados, segunda.documentos_eliminados) == (0, 0)
        assert RetencionEjecutada.objects.count() == 2
        assert LogAuditoria.objects.filter(accion="ejecutar retención (manual)").count() == 2


class TestIntereses:
    def test_anonimiza_tras_el_cierre_mas_la_retencion(self, ofertas):
        vieja = ConvocatoriaInteres.objects.create(
            anio_academico="2023-2024", fecha_inicio=HOY - timedelta(days=900), fecha_cierre=HOY - timedelta(days=800), estado="cerrada"
        )
        reciente = ConvocatoriaInteres.objects.create(anio_academico="2026-2027", fecha_inicio=HOY, fecha_cierre=HOY, estado="cerrada")
        for i, convocatoria in enumerate([vieja, vieja, reciente]):
            ExpresionInteres.objects.create(
                convocatoria=convocatoria, oferta=ofertas["informatica_facultad"] if i else ofertas["derecho_cum"], nombre=f"Persona {i}",
                ci=f"9001011230{i}", celular="55111111", email=f"p{i}@nauta.cu",
            )

        ejecucion = services.ejecutar()

        assert ejecucion.intereses_anonimizados == 2
        anonimas = ExpresionInteres.objects.filter(convocatoria=vieja)
        assert set(anonimas.values_list("nombre", flat=True)) == {"Interesado anonimizado"}
        assert all((e.ci, e.email, e.celular) == ("", "", "") for e in anonimas)
        assert anonimas.values("ci_hash").distinct().count() == 2  # sigue siendo único por oferta
        assert set(anonimas.values_list("oferta__carrera__nombre", flat=True)) == {"Derecho", "Ingeniería Informática"}
        assert ExpresionInteres.objects.get(convocatoria=reciente).nombre == "Persona 2"


class TestApi:
    URL = "/api/v1/admin/retencion/"

    def test_vista_previa_y_ejecucion_del_superadmin(self, api_como, superadmin, publicado):
        client = api_como(superadmin)

        vista = client.get(f"{self.URL}previsualizar/").json()
        assert set(vista) == {"aspirantes", "intereses", "documentos", "espacio_mb", "solo_versiones_antiguas"}
        assert client.post(f"{self.URL}ejecuciones/", {"confirmar": False}, format="json").status_code == 400
        ejecucion = client.post(f"{self.URL}ejecuciones/", {"confirmar": True}, format="json")
        assert (ejecucion.status_code, ejecucion.json()["automatica"]) == (201, False)
        assert client.get(f"{self.URL}ejecuciones/").json()[0]["id"] == ejecucion.json()["id"]

    def test_otros_roles_no_ejecutan(self, api_como, usuarios):  # noqa: F811
        assert api_como(usuarios["jefe"]).post(f"{self.URL}ejecuciones/", {"confirmar": True}, format="json").status_code == 403

    def test_tarea_mensual(self, publicado):
        from apps.retencion.tasks import aplicar_retencion

        pk = aplicar_retencion()

        assert RetencionEjecutada.objects.get(pk=pk).automatica is True
