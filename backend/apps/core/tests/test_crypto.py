import base64
from io import StringIO

import pytest
from cryptography.exceptions import InvalidTag
from django.core.management import call_command

from apps.core import crypto
from apps.core.fields import CampoCifrado


def test_cifrar_y_descifrar_recupera_el_valor():
    assert crypto.descifrar(crypto.cifrar("98042512345")) == "98042512345"


def test_el_mismo_valor_produce_cifrados_distintos():
    assert crypto.cifrar("maria@nauta.cu") != crypto.cifrar("maria@nauta.cu")


def test_el_cifrado_no_contiene_el_valor_en_claro():
    assert "98042512345" not in crypto.cifrar("98042512345")


def test_descifrar_detecta_manipulacion():
    token = crypto.cifrar("55123456")
    crudo = bytearray(base64.b64decode(token[3:]))
    crudo[-1] ^= 1
    with pytest.raises(InvalidTag):
        crypto.descifrar("v1:" + base64.b64encode(bytes(crudo)).decode())


def test_descifrar_rechaza_formato_desconocido():
    with pytest.raises(ValueError):
        crypto.descifrar("texto-plano")


def test_hash_busqueda_es_determinista_y_normaliza():
    assert crypto.hash_busqueda("Maria@Nauta.cu ") == crypto.hash_busqueda("maria@nauta.cu")
    assert crypto.hash_busqueda("98042512345") != crypto.hash_busqueda("98042512346")


def test_clave_de_longitud_incorrecta_falla(settings):
    settings.FIELD_ENCRYPTION_KEY = base64.b64encode(b"corta").decode()
    with pytest.raises(ValueError):
        crypto.cifrar("x")


def test_campo_cifrado_guarda_cifrado_y_lee_en_claro():
    campo = CampoCifrado()
    guardado = campo.get_prep_value("98042512345")

    assert guardado.startswith("v1:")
    assert campo.from_db_value(guardado, None, None) == "98042512345"


@pytest.mark.parametrize("vacio", [None, ""])
def test_campo_cifrado_respeta_vacios(vacio):
    campo = CampoCifrado()
    assert campo.get_prep_value(vacio) == vacio
    assert campo.from_db_value(vacio, None, None) == vacio


def test_comando_generar_clave_produce_32_bytes():
    salida = StringIO()
    call_command("generar_clave", stdout=salida)
    assert len(base64.b64decode(salida.getvalue().strip())) == 32
