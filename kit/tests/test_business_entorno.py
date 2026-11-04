"""Reglas de las variables de entorno del kit: el prefijo propio manda y el alias es respaldo."""

import pytest
from psxdecomp.entorno import VARIABLES_PROPIAS, Variables


def test_el_prefijo_propio_gana_al_alias_del_proyecto() -> None:
    variables = Variables(alias="JUEGO")
    entorno = {"JUEGO_DISC": "alias", "PSXDECOMP_DISC": "propio"}
    assert variables.leer("DISC", entorno) == "propio"


def test_el_alias_se_acepta_si_el_prefijo_propio_no_esta_definido_o_esta_vacio() -> None:
    variables = Variables(alias="JUEGO")
    assert variables.leer("DISC", {"JUEGO_DISC": "alias"}) == "alias"
    assert variables.leer("DISC", {"PSXDECOMP_DISC": "", "JUEGO_DISC": "alias"}) == "alias"


def test_sin_variables_definidas_no_hay_valor() -> None:
    assert Variables(alias="JUEGO").leer("DISC", {"OTRA_DISC": "x"}) is None


def test_un_alias_igual_al_prefijo_propio_se_consulta_una_sola_vez() -> None:
    assert Variables(alias="PSXDECOMP").nombres("DISC") == ("PSXDECOMP_DISC",)
    assert VARIABLES_PROPIAS.nombres("DISC") == ("PSXDECOMP_DISC",)


def test_las_variables_definidas_incluyen_los_valores_vacios_en_orden_de_precedencia() -> None:
    variables = Variables(alias="JUEGO")
    entorno = {"JUEGO_X1": "b", "PSXDECOMP_X1": ""}
    assert list(variables.definidas("X1", entorno)) == ["", "b"]


def test_el_nombre_del_proyecto_usa_el_alias_y_sin_alias_el_prefijo_propio() -> None:
    assert Variables(alias="JUEGO").nombre_del_proyecto("DISC") == "JUEGO_DISC"
    assert VARIABLES_PROPIAS.nombre_del_proyecto("DISC") == "PSXDECOMP_DISC"


def test_la_descripcion_nombra_las_dos_variables() -> None:
    assert Variables(alias="JUEGO").describir("7ZIP") == "PSXDECOMP_7ZIP (o JUEGO_7ZIP)"
    assert VARIABLES_PROPIAS.describir("7ZIP") == "PSXDECOMP_7ZIP"


@pytest.mark.parametrize("sufijo", ["disc", "", "CON ESPACIO", "A=B", "-INICIO", "X" * 65])
def test_un_sufijo_que_no_es_identificador_en_mayusculas_se_rechaza(sufijo: str) -> None:
    with pytest.raises(ValueError, match="sufijo"):
        VARIABLES_PROPIAS.nombres(sufijo)


@pytest.mark.parametrize("prefijo", ["juego", "", "CON ESPACIO", "A=B", "_X"])
def test_un_alias_que_no_es_identificador_en_mayusculas_se_rechaza(prefijo: str) -> None:
    with pytest.raises(ValueError, match="prefijo"):
        Variables(alias=prefijo)
    with pytest.raises(ValueError, match="prefijo"):
        Variables(prefijo_principal=prefijo)


def test_un_sufijo_de_exactamente_64_caracteres_es_valido() -> None:
    sufijo = "X" * 64
    assert VARIABLES_PROPIAS.nombres(sufijo) == (f"PSXDECOMP_{sufijo}",)
    assert VARIABLES_PROPIAS.leer(sufijo, {f"PSXDECOMP_{sufijo}": "valor"}) == "valor"
