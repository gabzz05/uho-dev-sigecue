"""Fixtures del portal del aspirante, compartidas por los tests de aspirantes y solicitudes."""

import io
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from apps.aspirantes import services
from apps.aspirantes.models import TipoDocumento
from apps.convocatorias.models import ConvocatoriaSolicitud
from apps.nomencladores.models import Carrera, CumFum, Municipio
from apps.oferta.models import OfertaCarrera
from apps.plan_plazas.models import PlanPlazas
from apps.roles.models import Rol
from apps.users.models import Usuario

ANIO = "2026-2027"
HOY = timezone.localdate()


def png(nombre="foto.png", tamano=(10, 10)):
    contenido = io.BytesIO()
    Image.new("RGB", tamano, "blue").save(contenido, "PNG")
    return SimpleUploadedFile(nombre, contenido.getvalue(), content_type="image/png")


def pdf(nombre="certificacion.pdf", relleno=0):
    return SimpleUploadedFile(nombre, b"%PDF-1.4\n" + b"0" * relleno + b"\n%%EOF", content_type="application/pdf")


@pytest.fixture
def crear_aspirante(db):
    def _crear(username="asp_maria", ci="98042512345", email="maria@nauta.cu", **extra):
        datos = {
            "first_name": "María", "last_name": "González Pérez", "celular": "55123456",
            "email_verificado": True, "privacidad_aceptada_at": timezone.now(),
        }
        usuario = Usuario(username=username, email=email, ci=ci, rol=Rol.objects.get(codigo=Rol.ASPIRANTE), **(datos | extra))
        usuario.set_password("Clave-Segura-123")
        usuario.save()
        return usuario

    return _crear


@pytest.fixture
def aspirante(crear_aspirante):
    return crear_aspirante()


@pytest.fixture
def completar_perfil():
    """Deja el perfil listo para elegir carreras: foto, centro de trabajo, índice y documentos."""

    def _completar(usuario):
        usuario.foto.save("foto.png", ContentFile(png().read()))
        services.actualizar_datos(usuario, {"centro_trabajo": "Empresa Eléctrica", "indice_declarado": Decimal("92.5")})
        for tipo in TipoDocumento.objects.filter(activo=True):
            services.subir_documento(usuario, tipo, pdf(), "PDF")
        return services.perfil_de(usuario)

    return _completar


@pytest.fixture
def perfil_listo(aspirante, completar_perfil):
    return completar_perfil(aspirante)


@pytest.fixture
def carreras(db):
    return {
        "informatica": Carrera.objects.create(nombre="Ingeniería Informática", codigo="II", duracion_anios=5),
        "derecho": Carrera.objects.create(nombre="Derecho", codigo="DER", duracion_anios=5),
    }


@pytest.fixture
def otro_cum(db):
    return CumFum.objects.create(nombre="CUM Banes", codigo="CUMB", tipo="CUM", municipio=Municipio.objects.get(nombre="Banes"))


@pytest.fixture
def ofertas(db, facultad, cum, otro_cum, carreras):
    PlanPlazas.objects.create(anio_academico=ANIO, estado=PlanPlazas.Estado.PUBLICADO, fecha_aprobacion=timezone.now())
    crear = OfertaCarrera.objects.create
    return {
        "informatica_facultad": crear(carrera=carreras["informatica"], facultad=facultad, anio_academico=ANIO, plazas_plan=80),
        "informatica_cum": crear(carrera=carreras["informatica"], cum_fum=cum, anio_academico=ANIO, plazas_plan=10),
        "informatica_banes": crear(carrera=carreras["informatica"], cum_fum=otro_cum, anio_academico=ANIO, plazas_plan=10),
        "derecho_cum": crear(carrera=carreras["derecho"], cum_fum=cum, anio_academico=ANIO, plazas_plan=5),
        "sin_plazas": crear(carrera=carreras["derecho"], facultad=facultad, anio_academico=ANIO, plazas_plan=0),
    }


@pytest.fixture
def convocatoria(ofertas):
    return ConvocatoriaSolicitud.objects.create(
        anio_academico=ANIO, fecha_inicio=HOY, fecha_cierre=HOY + timedelta(days=20), estado=ConvocatoriaSolicitud.Estado.ABIERTA
    )


def cerrar(convocatoria):
    ConvocatoriaSolicitud.objects.filter(pk=convocatoria.pk).update(estado=ConvocatoriaSolicitud.Estado.CERRADA)
    convocatoria.refresh_from_db()
