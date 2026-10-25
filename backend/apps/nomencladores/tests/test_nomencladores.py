import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from PIL import Image

from apps.nomencladores.models import Area, Cargo, Carrera, CumFum, Departamento, Facultad, Municipio

pytestmark = pytest.mark.django_db

BASE = "/api/v1/admin/nomencladores"


def errores(response):
    return response.json()["error"]["detalles"]


def imagen():
    contenido = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(contenido, "PNG")
    return SimpleUploadedFile("carrera.png", contenido.getvalue(), content_type="image/png")


@pytest.fixture
def jefe_ci(crear_usuario):
    return crear_usuario("jefe", rol="jefe_ci")


@pytest.fixture
def admin_facultad(crear_usuario, facultad):
    return crear_usuario("admin_fac", rol="admin_facultad", facultad=facultad)


CARRERA = {"nombre": "Ingeniería Informática", "codigo": "II", "duracion_anios": 5}


class TestDatosIniciales:
    def test_14_municipios_de_holguin(self):
        assert Municipio.objects.filter(provincia="Holguín").count() == 14

    def test_municipio_unico_por_provincia(self):
        with pytest.raises(IntegrityError):
            Municipio.objects.create(nombre="Moa", provincia="Holguín")


class TestPermisos:
    def test_lectura_requiere_permiso(self, api_como, crear_usuario, facultad):
        jefe_area = crear_usuario("ja", rol="jefe_area_facultad", facultad=facultad)

        assert api_como(jefe_area).get(f"{BASE}/carreras/").status_code == 403

    def test_rol_local_lee_catalogos_globales(self, api_como, admin_facultad):
        assert api_como(admin_facultad).get(f"{BASE}/municipios/").json()["count"] == 14

    @pytest.mark.parametrize("ruta", ["carreras", "facultades", "cum-fum", "municipios", "cargos"])
    def test_rol_local_no_modifica_catalogos_globales(self, api_como, admin_facultad, ruta):
        response = api_como(admin_facultad).post(f"{BASE}/{ruta}/", {"nombre": "X"}, format="json")

        assert response.status_code == 403
        assert "Comisión de Ingreso" in response.json()["error"]["mensaje"]

    def test_rol_global_con_permiso_crea_carreras(self, api_como, jefe_ci):
        response = api_como(jefe_ci).post(f"{BASE}/carreras/", CARRERA, format="json")

        assert response.status_code == 201
        assert response.json()["modalidad"] == "por_encuentro"
        assert response.json()["modalidad_nombre"] == "Por encuentro"

    def test_rol_global_sin_permiso_de_escritura_no_crea(self, api_como, crear_usuario):
        vicerrector = crear_usuario("vr", rol="vicerrector")

        assert api_como(vicerrector).post(f"{BASE}/carreras/", CARRERA, format="json").status_code == 403


class TestCarreras:
    def test_duracion_entre_1_y_8(self, api_como, jefe_ci):
        response = api_como(jefe_ci).post(f"{BASE}/carreras/", CARRERA | {"duracion_anios": 0}, format="json")

        assert "duracion_anios" in errores(response)

    def test_codigo_unico(self, api_como, jefe_ci):
        client = api_como(jefe_ci)
        client.post(f"{BASE}/carreras/", CARRERA, format="json")

        assert "codigo" in errores(client.post(f"{BASE}/carreras/", CARRERA, format="json"))

    def test_imagen_va_al_almacenamiento_publico(self, api_como, jefe_ci, settings):
        response = api_como(jefe_ci).post(f"{BASE}/carreras/", CARRERA | {"imagen": imagen()}, format="multipart")

        assert response.status_code == 201
        assert "/media/carreras/" in response.json()["imagen"]
        assert any((settings.PUBLIC_MEDIA_ROOT / "carreras").iterdir())
        assert not (settings.MEDIA_ROOT / "carreras").exists()

    def test_quitar_imagen_enviando_el_campo_vacio(self, api_como, jefe_ci):
        carrera = Carrera.objects.create(**CARRERA, imagen="carreras/vieja.png")

        response = api_como(jefe_ci).patch(f"{BASE}/carreras/{carrera.pk}/", {"imagen": ""}, format="multipart")

        assert response.status_code == 200
        carrera.refresh_from_db()
        assert not carrera.imagen

    def test_filtros_y_busqueda(self, api_como, jefe_ci):
        Carrera.objects.create(**CARRERA)
        Carrera.objects.create(nombre="Contabilidad y Finanzas", codigo="CF", duracion_anios=4, activo=False)
        client = api_como(jefe_ci)

        assert client.get(f"{BASE}/carreras/", {"buscar": "infor"}).json()["count"] == 1
        assert client.get(f"{BASE}/carreras/", {"buscar": "CF"}).json()["count"] == 1
        assert client.get(f"{BASE}/carreras/", {"activo": "false"}).json()["count"] == 1
        assert client.get(f"{BASE}/carreras/", {"duracion": 5}).json()["count"] == 1

    def test_desactivar(self, api_como, jefe_ci):
        carrera = Carrera.objects.create(**CARRERA)

        api_como(jefe_ci).patch(f"{BASE}/carreras/{carrera.pk}/", {"activo": False}, format="json")

        carrera.refresh_from_db()
        assert not carrera.activo


class TestEntidades:
    def test_crea_facultad_con_municipio(self, api_como, jefe_ci, municipio):
        response = api_como(jefe_ci).post(
            f"{BASE}/facultades/", {"nombre": "Fac. Informática", "codigo": "FI", "municipio": municipio.pk}, format="json"
        )

        assert response.status_code == 201
        assert response.json()["municipio_nombre"] == "Holguín"

    def test_crea_cum_y_filtra_por_tipo(self, api_como, jefe_ci, municipio):
        client = api_como(jefe_ci)
        client.post(f"{BASE}/cum-fum/", {"nombre": "CUM Moa", "codigo": "CM", "tipo": "CUM", "municipio": municipio.pk}, format="json")
        client.post(f"{BASE}/cum-fum/", {"nombre": "FUM Gibara", "codigo": "FG", "tipo": "FUM", "municipio": municipio.pk}, format="json")

        assert client.get(f"{BASE}/cum-fum/", {"tipo": "FUM"}).json()["count"] == 1

    def test_no_borra_un_municipio_en_uso(self, api_como, superadmin, facultad):
        response = api_como(superadmin).delete(f"{BASE}/municipios/{facultad.municipio_id}/")

        assert response.status_code == 400
        assert "desactivarlo" in response.json()["error"]["mensaje"]

    def test_borra_un_registro_sin_uso(self, api_como, superadmin):
        cargo = Cargo.objects.create(nombre="Asesor")

        assert api_como(superadmin).delete(f"{BASE}/cargos/{cargo.pk}/").status_code == 204


class TestAreasYDepartamentos:
    def test_admin_local_crea_area_en_su_entidad_sin_indicarla(self, api_como, admin_facultad, facultad):
        response = api_como(admin_facultad).post(f"{BASE}/areas/", {"nombre": "Software"}, format="json")

        assert response.status_code == 201
        assert Area.objects.get().facultad == facultad
        assert response.json()["entidad_nombre"] == facultad.nombre

    def test_admin_local_no_crea_areas_en_otra_entidad(self, api_como, admin_facultad, otra_facultad):
        response = api_como(admin_facultad).post(
            f"{BASE}/areas/", {"nombre": "X", "facultad": otra_facultad.pk}, format="json"
        )

        assert "propia entidad" in errores(response)["facultad"][0]

    def test_rol_global_debe_indicar_una_sola_entidad(self, api_como, jefe_ci, facultad, cum):
        client = api_como(jefe_ci)

        assert "facultad" in errores(client.post(f"{BASE}/areas/", {"nombre": "X"}, format="json"))
        ambas = client.post(f"{BASE}/areas/", {"nombre": "X", "facultad": facultad.pk, "cum_fum": cum.pk}, format="json")
        assert "facultad" in errores(ambas)

    def test_rol_local_solo_ve_areas_de_su_entidad(self, api_como, admin_facultad, facultad, otra_facultad):
        Area.objects.create(nombre="Propia", facultad=facultad)
        Area.objects.create(nombre="Ajena", facultad=otra_facultad)

        nombres = [a["nombre"] for a in api_como(admin_facultad).get(f"{BASE}/areas/").json()["results"]]

        assert nombres == ["Propia"]

    def test_rol_local_sin_entidad_no_ve_nada(self, api_como, crear_usuario, facultad):
        Area.objects.create(nombre="Propia", facultad=facultad)
        huerfano = crear_usuario("sin_entidad", rol="admin_facultad")

        assert api_como(huerfano).get(f"{BASE}/areas/").json()["count"] == 0

    def test_rol_global_ve_todas_y_filtra(self, api_como, jefe_ci, facultad, cum):
        Area.objects.create(nombre="A", facultad=facultad)
        Area.objects.create(nombre="B", cum_fum=cum)
        client = api_como(jefe_ci)

        assert client.get(f"{BASE}/areas/").json()["count"] == 2
        assert client.get(f"{BASE}/areas/", {"cum_fum": cum.pk}).json()["count"] == 1

    def test_departamentos_solo_en_areas_de_su_entidad(self, api_como, admin_facultad, facultad, otra_facultad):
        propia = Area.objects.create(nombre="Propia", facultad=facultad)
        ajena = Area.objects.create(nombre="Ajena", facultad=otra_facultad)
        Departamento.objects.create(nombre="Dpto ajeno", area=ajena)
        client = api_como(admin_facultad)

        assert client.post(f"{BASE}/departamentos/", {"nombre": "Programación", "area": propia.pk}, format="json").status_code == 201
        assert "area" in errores(client.post(f"{BASE}/departamentos/", {"nombre": "X", "area": ajena.pk}, format="json"))
        assert [d["nombre"] for d in client.get(f"{BASE}/departamentos/").json()["results"]] == ["Programación"]

    def test_la_base_de_datos_exige_una_sola_entidad_en_el_area(self, facultad, cum):
        with pytest.raises(IntegrityError):
            Area.objects.create(nombre="Doble", facultad=facultad, cum_fum=cum)


def test_queda_auditado(api_como, jefe_ci):
    from apps.auditoria.models import LogAuditoria

    api_como(jefe_ci).post(f"{BASE}/carreras/", CARRERA, format="json")

    assert LogAuditoria.objects.get().modulo == "nomencladores"


def test_str_de_los_modelos(facultad, cum):
    area = Area.objects.create(nombre="Software", facultad=facultad)
    assert [str(x) for x in (facultad, cum, area, Departamento(nombre="D", area=area), Cargo(nombre="C"))] == [
        "Facultad de Informática", "CUM Calixto García", "Software", "D", "C",
    ]
    assert str(Carrera(nombre="Derecho")) == "Derecho"
    assert isinstance(Facultad.objects.first(), Facultad) and isinstance(CumFum.objects.first(), CumFum)
