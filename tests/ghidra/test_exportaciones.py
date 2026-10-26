from pathlib import Path

import pytest
from tools.ghidra import exportaciones
from tools.ghidra.exportaciones import (
    COLUMNAS_CADENAS,
    COLUMNAS_XREFS,
    Cadena,
    ReferenciaDato,
    leer_cadenas_csv,
    leer_xrefs_csv,
    parsear_cadenas_csv,
    parsear_xrefs_csv,
)

CABECERA_XREFS = ",".join(COLUMNAS_XREFS)
CABECERA_CADENAS = ",".join(COLUMNAS_CADENAS)


def test_interpreta_las_referencias_de_datos() -> None:
    texto = f"{CABECERA_XREFS}\n0x80010000,4,0x80014C54;0x80014E24,17,16\n0x80010001,0,,0,1\n"
    assert parsear_xrefs_csv(texto) == [
        ReferenciaDato(0x80010000, 4, (0x80014C54, 0x80014E24), 17, 16),
        ReferenciaDato(0x80010001, 0, (), 0, 1),
    ]


@pytest.mark.parametrize(
    ("fila", "mensaje"),
    [
        ("0x80010000,4,0x80014C54", "fila 2: se esperaban 5 campos"),
        ("80010000,4,,0,0", "fila 2: direccion_dato debe empezar por 0x"),
        ("0xZZ,4,,0,0", "fila 2: direccion_dato no es hexadecimal"),
        ("0x100000000,4,,0,0", "fila 2: direccion_dato excede 32 bits"),
        ("0x80010000,x,,0,0", "fila 2: tamano no es un entero"),
        ("0x80010000,-1,,0,0", "fila 2: tamano=-1 fuera de rango"),
        ("0x80010000,4,,0,99999999", "fila 2: escrituras=99999999 fuera de rango"),
        ("0x80010000,4,abc,0,0", "fila 2: funciones_que_lo_usan debe empezar por 0x"),
    ],
)
def test_rechaza_filas_de_referencias_invalidas(fila: str, mensaje: str) -> None:
    with pytest.raises(ValueError, match=mensaje):
        parsear_xrefs_csv(f"{CABECERA_XREFS}\n{fila}\n")


def test_rechaza_cabecera_vacia_o_distinta() -> None:
    with pytest.raises(ValueError, match="xrefs_datos.csv: la cabecera no coincide"):  # noqa: RUF043
        parsear_xrefs_csv("")
    with pytest.raises(ValueError, match="strings.csv: la cabecera no coincide"):  # noqa: RUF043
        parsear_cadenas_csv("direccion,texto\n")


def test_las_cotas_de_filas_y_de_funciones_por_dato_se_aplican(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(exportaciones, "MAX_FILAS", 1)
    with pytest.raises(ValueError, match="xrefs_datos.csv: mas de 1 filas"):  # noqa: RUF043
        parsear_xrefs_csv(f"{CABECERA_XREFS}\n0x80010000,4,,0,0\n0x80010004,4,,0,0\n")
    monkeypatch.setattr(exportaciones, "MAX_FUNCIONES_POR_DATO", 1)
    with pytest.raises(ValueError, match="funciones_que_lo_usan excede 1"):
        parsear_xrefs_csv(f"{CABECERA_XREFS}\n0x80010000,4,0x80014C54;0x80014E24,0,0\n")


def test_interpreta_las_cadenas_con_comas_y_saltos_de_linea() -> None:
    texto = f'{CABECERA_CADENAS}\n0x80067C7C,3,"hola, mundo\n"\n0x80067EF0,2,ab\n'
    assert parsear_cadenas_csv(texto) == [
        Cadena(0x80067C7C, 3, "hola, mundo\n"),
        Cadena(0x80067EF0, 2, "ab"),
    ]


def test_rechaza_cadenas_demasiado_largas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(exportaciones, "MAX_LONGITUD_TEXTO", 3)
    with pytest.raises(ValueError, match="fila 2: texto excede 3 caracteres"):
        parsear_cadenas_csv(f"{CABECERA_CADENAS}\n0x80067C7C,4,abcd\n")


def test_leer_desde_disco_acota_el_tamano_y_exige_utf8(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ruta = tmp_path / "xrefs_datos.csv"
    ruta.write_text(f"{CABECERA_XREFS}\n0x80010000,4,,1,0\n", encoding="utf-8")
    assert leer_xrefs_csv(ruta) == [ReferenciaDato(0x80010000, 4, (), 1, 0)]
    cadenas = tmp_path / "strings.csv"
    cadenas.write_text(f"{CABECERA_CADENAS}\n0x80067C7C,2,ab\n", encoding="utf-8")
    assert leer_cadenas_csv(cadenas) == [Cadena(0x80067C7C, 2, "ab")]
    ruta.write_bytes(b"\xff\xfe\xfa")
    with pytest.raises(ValueError, match="xrefs_datos.csv: la codificacion no es UTF-8"):  # noqa: RUF043
        leer_xrefs_csv(ruta)
    monkeypatch.setattr(exportaciones, "MAX_BYTES_CSV", 2)
    with pytest.raises(ValueError, match="strings.csv: el archivo excede 2 bytes"):  # noqa: RUF043
        leer_cadenas_csv(cadenas)
