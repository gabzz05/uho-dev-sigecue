from datetime import timedelta

import pytest
from django.core import mail
from django.db import IntegrityError
from django.utils import timezone

from apps.convocatorias import services
from apps.convocatorias.models import ConvocatoriaSolicitud
from apps.convocatorias.tasks import cerrar_convocatorias_vencidas, notificar_interesados
from apps.interes.models import ConvocatoriaInteres, ExpresionInteres
from apps.nomencladores.models import Carrera
from apps.notificaciones.models import Notificacion
from apps.oferta.models import OfertaCarrera
from apps.plan_plazas.models import PlanPlazas

pytestmark = pytest.mark.django_db

URL = "/api/v1/admin/convocatorias/"
ANIO = "2026-2027"
HOY = timezone.localdate()


@pytest.fixture
def jefe_ci(crear_usuario):
    return crear_usuario("jefe", rol="jefe_ci")


@pytest.fixture
def informatica(db):
    return Carrera.objects.create(nombre="Ingeniería Informática", codigo="II", duracion_anios=5)


@pytest.fixture
def plan_publicado(db, facultad, cum, informatica):
    plan = PlanPlazas.objects.create(anio_academico=ANIO, estado=PlanPlazas.Estado.PUBLICADO, fecha_aprobacion=timezone.now())
    OfertaCarrera.objects.create(carrera=informatica, facultad=facultad, anio_academico=ANIO, plazas_plan=80)
    OfertaCarrera.objects.create(carrera=informatica, cum_fum=cum, anio_academico=ANIO, plazas_plan=0)
    return plan


@pytest.fixture
def convocatoria(db):
    return ConvocatoriaSolicitud.objects.create(anio_academico=ANIO, fecha_inicio=HOY, fecha_cierre=HOY + timedelta(days=20))


def datos(**extra):
    return {"anio_academico": ANIO, "fecha_inicio": str(HOY), "fecha_cierre": str(HOY + timedelta(days=20))} | extra


class TestCreacion:
    def test_la_primera_es_la_numero_1(self, api_como, jefe_ci):
        response = api_como(jefe_ci).post(URL, datos(), format="json")

        assert response.status_code == 201
        assert (response.json()["numero"], response.json()["estado"]) == (1, "borrador")

    def test_la_segunda_exige_cerrar_la_primera(self, api_como, jefe_ci, convocatoria):
        client = api_como(jefe_ci)

        assert "no está cerrada" in client.post(URL, datos(), format="json").json()["error"]["mensaje"]
        ConvocatoriaSolicitud.objects.filter(pk=convocatoria.pk).update(estado="cerrada")
        assert client.post(URL, datos(), format="json").json()["numero"] == 2

    def test_con_entidades_seleccionadas(self, api_como, jefe_ci, facultad, cum):
        response = api_como(jefe_ci).post(URL, datos(facultades=[facultad.pk], cum_fums=[cum.pk]), format="json")

        assert sorted(response.json()["entidades"]) == ["CUM Calixto García", "Facultad de Informática"]

    def test_solo_roles_globales(self, api_como, crear_usuario, facultad):
        admin = crear_usuario("admin_fac", rol="admin_facultad", facultad=facultad)

        assert api_como(admin).post(URL, datos(), format="json").status_code == 403

    def test_fechas(self, api_como, jefe_ci):
        response = api_como(jefe_ci).post(URL, datos(fecha_cierre=str(HOY - timedelta(days=1))), format="json")

        assert "fecha_cierre" in response.json()["error"]["detalles"]

    def test_la_base_de_datos_impide_repetir_numero(self, convocatoria):
        with pytest.raises(IntegrityError):
            ConvocatoriaSolicitud.objects.create(anio_academico=ANIO, numero=1, fecha_inicio=HOY, fecha_cierre=HOY)


class TestApertura:
    def test_exige_plan_publicado(self, api_como, jefe_ci, convocatoria):
        response = api_como(jefe_ci).post(f"{URL}{convocatoria.pk}/abrir/")

        assert "plan de plazas 2026-2027 todavía no está publicado" in response.json()["error"]["mensaje"]

    def test_un_plan_sin_publicar_no_cuenta(self, jefe_ci, convocatoria):
        PlanPlazas.objects.create(anio_academico=ANIO, estado=PlanPlazas.Estado.EN_APROBACION)

        with pytest.raises(Exception, match="no está publicado"):
            services.abrir(convocatoria)

    def test_abre_con_plan_publicado(self, api_como, jefe_ci, convocatoria, plan_publicado):
        datos_respuesta = api_como(jefe_ci).post(f"{URL}{convocatoria.pk}/abrir/").json()

        assert datos_respuesta["estado"] == "abierta"
        assert datos_respuesta["total_ofertas"] == 1  # La oferta con 0 plazas no cuenta.

    def test_entidades_sin_plazas(self, jefe_ci, convocatoria, plan_publicado, cum):
        convocatoria.cum_fums.set([cum])

        with pytest.raises(Exception, match="no tienen plazas"):
            services.abrir(convocatoria)

    def test_solo_una_abierta(self, jefe_ci, convocatoria, plan_publicado):
        services.abrir(convocatoria)
        services.cerrar(convocatoria)
        segunda = ConvocatoriaSolicitud.objects.create(anio_academico=ANIO, numero=2, fecha_inicio=HOY, fecha_cierre=HOY)
        ConvocatoriaSolicitud.objects.filter(pk=convocatoria.pk).update(estado="abierta")

        with pytest.raises(Exception, match="otra convocatoria"):
            services.abrir(segunda)

    def test_abierta_no_cambia_entidades(self, api_como, jefe_ci, convocatoria, plan_publicado, facultad):
        services.abrir(convocatoria)

        response = api_como(jefe_ci).patch(f"{URL}{convocatoria.pk}/", {"facultades": [facultad.pk]}, format="json")

        assert response.status_code == 400

    def test_cierre_automatico(self, convocatoria, plan_publicado):
        services.abrir(convocatoria)
        ConvocatoriaSolicitud.objects.filter(pk=convocatoria.pk).update(
            fecha_inicio=HOY - timedelta(days=10), fecha_cierre=HOY - timedelta(days=1)
        )

        assert cerrar_convocatorias_vencidas() == 1
        convocatoria.refresh_from_db()
        assert convocatoria.estado == "cerrada"


class TestAvisoAInteresados:
    @pytest.fixture
    def interesados(self, informatica, facultad, cum):
        oferta = OfertaCarrera.objects.create(carrera=informatica, facultad=facultad, anio_academico=ANIO, plazas_plan=80)
        otra = OfertaCarrera.objects.create(carrera=informatica, cum_fum=cum, anio_academico=ANIO, plazas_plan=10)
        interes = ConvocatoriaInteres.objects.create(anio_academico=ANIO, fecha_inicio=HOY, fecha_cierre=HOY, estado="cerrada")
        PlanPlazas.objects.create(anio_academico=ANIO, estado=PlanPlazas.Estado.PUBLICADO, fecha_aprobacion=timezone.now())

        def expresion(oferta_, nombre, ci, email):
            ExpresionInteres.objects.create(convocatoria=interes, oferta=oferta_, nombre=nombre, ci=ci, celular="55123456", email=email)

        expresion(oferta, "Pedro Pérez", "90010112345", "pedro@nauta.cu")
        expresion(otra, "Pedro Pérez", "90010112345", "pedro@nauta.cu")  # Misma persona, dos carreras.
        expresion(oferta, "María González", "98042512345", "maria.interes@nauta.cu")
        # Interesado de otro año: no se avisa.
        vieja = ConvocatoriaInteres.objects.create(anio_academico="2025-2026", fecha_inicio=HOY, fecha_cierre=HOY, estado="cerrada")
        viejo = OfertaCarrera.objects.create(carrera=informatica, facultad=facultad, anio_academico="2025-2026")
        ExpresionInteres.objects.create(convocatoria=vieja, oferta=viejo, nombre="Luis", ci="01081923456", celular="55000000", email="luis@nauta.cu")

    def test_un_correo_por_persona_e_in_app_si_tiene_cuenta(self, crear_usuario, convocatoria, interesados, django_capture_on_commit_callbacks):
        # María ya tiene cuenta de aspirante (con otro email).
        maria = crear_usuario("asp_maria", rol="aspirante", ci="98042512345", email="maria@nauta.cu", email_verificado=True, first_name="María")

        with django_capture_on_commit_callbacks(execute=True):
            services.abrir(convocatoria)

        destinatarios = sorted(m.to[0] for m in mail.outbox)
        assert destinatarios == ["maria@nauta.cu", "pedro@nauta.cu"]
        assert Notificacion.objects.get(usuario=maria).tipo == "convocatoria_solicitud_abierta"
        convocatoria.refresh_from_db()
        assert convocatoria.interesados_notificados == 2
        assert "Pedro" in next(m.body for m in mail.outbox if m.to == ["pedro@nauta.cu"])

    def test_en_la_segunda_convocatoria_no_se_repite(self, convocatoria, interesados, django_capture_on_commit_callbacks):
        ConvocatoriaSolicitud.objects.filter(pk=convocatoria.pk).update(estado="cerrada")
        segunda = ConvocatoriaSolicitud.objects.create(anio_academico=ANIO, numero=2, fecha_inicio=HOY, fecha_cierre=HOY + timedelta(days=5))

        with django_capture_on_commit_callbacks(execute=True):
            services.abrir(segunda)

        assert mail.outbox == []

    def test_la_tarea_devuelve_el_total(self, convocatoria, interesados):
        assert notificar_interesados(convocatoria.pk) == 2


class TestPublico:
    def test_convocatoria_activa(self, api, convocatoria, plan_publicado):
        services.abrir(convocatoria)

        datos_respuesta = api.get("/api/v1/convocatorias/activa/").json()["convocatoria"]

        assert (datos_respuesta["anio_academico"], datos_respuesta["numero"]) == (ANIO, 1)

    def test_sin_convocatoria_activa(self, api, convocatoria):
        assert api.get("/api/v1/convocatorias/activa/").json() == {"convocatoria": None}

    def test_abierta_pero_aun_no_empieza(self, api, convocatoria, plan_publicado):
        services.abrir(convocatoria)
        ConvocatoriaSolicitud.objects.filter(pk=convocatoria.pk).update(fecha_inicio=HOY + timedelta(days=3))

        assert api.get("/api/v1/convocatorias/activa/").json() == {"convocatoria": None}


def test_str(convocatoria):
    assert str(convocatoria) == "Convocatoria 1 de solicitud 2026-2027"
