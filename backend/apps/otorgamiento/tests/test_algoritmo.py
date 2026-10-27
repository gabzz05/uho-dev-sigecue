import pytest

from apps.otorgamiento.algoritmo import Candidato, PlazasInsuficientes, repartir

# Ofertas: 1 = Informática Facultad, 2 = Informática CUM, 3 = Derecho CUM.
ANA = Candidato(1, [(11, 1), (12, 3)])
LUIS = Candidato(2, [(21, 1), (22, 2)])
EVA = Candidato(3, [(31, 1), (32, 3)])


def test_cada_uno_toma_su_mejor_opcion_con_plaza_por_orden_de_ranking():
    asignacion, libres = repartir([ANA, LUIS, EVA], {1: 1, 2: 1, 3: 1})

    assert asignacion == {1: 11, 2: 22, 3: 32}
    assert libres == {1: 0, 2: 0, 3: 0}


def test_una_sola_plaza_por_aspirante_y_sin_plaza_si_no_alcanza():
    asignacion, _ = repartir([ANA, LUIS, EVA], {1: 1, 2: 0, 3: 1})

    assert asignacion == {1: 11, 2: None, 3: 32}


def test_el_orden_del_ranking_manda():
    asignacion, _ = repartir([EVA, ANA], {1: 1, 3: 1})

    assert asignacion == {3: 31, 1: 12}


def test_un_fijado_ocupa_su_plaza_y_libera_la_otra_en_cascada():
    # Se fija a Eva en Informática: Ana (mejor ranking) baja a Derecho y Luis no tiene dónde.
    asignacion, _ = repartir([ANA, LUIS, EVA], {1: 1, 2: 0, 3: 1}, fijados={3: 31})

    assert asignacion == {3: 31, 1: 12, 2: None}


def test_un_prohibido_salta_esa_opcion():
    asignacion, _ = repartir([ANA, LUIS], {1: 1, 2: 1, 3: 1}, prohibidos={(1, 11)})

    assert asignacion == {1: 12, 2: 21}


def test_nunca_se_supera_el_plan():
    with pytest.raises(PlazasInsuficientes) as error:
        repartir([ANA, LUIS, EVA], {1: 1}, fijados={1: 11, 2: 21})

    assert error.value.oferta_id == 1
