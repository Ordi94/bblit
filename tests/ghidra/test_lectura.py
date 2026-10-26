from pathlib import Path

import pytest
from tools.ghidra import lectura
from tools.ghidra.dominio import Funcion
from tools.ghidra.lectura import COLUMNAS_FUNCIONES, leer_funciones_csv, parsear_funciones_csv

from tests.ghidra.sintetica import MUESTRA, csv_funciones, fila


def test_parsear_la_muestra_produce_las_funciones_exactas() -> None:
    funciones = parsear_funciones_csv(MUESTRA)
    assert funciones[0] == Funcion(
        direccion=0x80014A00,
        nombre="__main",
        tamano=8,
        es_libreria=True,
        libreria_origen="2MBYTE.OBJ/2MBYTE.OBJ|LIBSN.LIB/SNMAIN.OBJ",
        llamadores=1,
        nombre_oficial=True,
        comentario="",
    )
    assert [f.nombre for f in funciones] == [
        "__main",
        "main",
        "FUN_80016c0c",
        "DecDCTReset",
        "LIBPRESS_OBJ_188",
    ]
    assert funciones[3].comentario == "Possible A.OBJ/uno\nPossible B.OBJ/dos"
    assert funciones[2].llamadores == 3


def test_parsear_acepta_solo_la_cabecera() -> None:
    assert parsear_funciones_csv(csv_funciones([])) == []


@pytest.mark.parametrize(
    ("texto", "mensaje"),
    [
        ("", "la cabecera no coincide"),
        ("direccion,nombre\n", "la cabecera no coincide"),
        (csv_funciones([], cabecera=tuple(reversed(COLUMNAS_FUNCIONES))), "la cabecera no coincide"),
    ],
)
def test_parsear_rechaza_cabeceras_incorrectas(texto: str, mensaje: str) -> None:
    with pytest.raises(ValueError, match=mensaje):
        parsear_funciones_csv(texto)


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"direccion": "80014A08"}, r"fila 2: direccion debe empezar por 0x"),
        ({"direccion": "0xZZ"}, r"fila 2: direccion no es hexadecimal"),
        ({"direccion": "0x8001"}, r"fila 2: direccion=0x00008001 fuera del segmento"),
        ({"direccion": "0x80069A00"}, r"fila 2: direccion=0x80069A00 fuera del segmento"),
        ({"direccion": "0x80014A0A"}, r"fila 2: direccion=0x80014A0A no alineada a 4"),
        ({"tamano": "abc"}, r"fila 2: tamano no es un entero"),
        ({"tamano": "0"}, r"fila 2: tamano=0 fuera de rango 1\.\.348160"),
        ({"tamano": "348161"}, r"fila 2: tamano=348161 fuera de rango"),
        ({"es_libreria": "2"}, r"fila 2: es_libreria debe ser 0 o 1"),
        ({"nombre_oficial": "si"}, r"fila 2: nombre_oficial debe ser 0 o 1"),
        ({"nombre": ""}, r"fila 2: nombre vacio"),
        ({"nombre": "x" * 129}, r"fila 2: nombre excede 128 caracteres"),
        ({"nombre": "a\x00b"}, r"fila 2: nombre contiene caracteres de control"),
        ({"libreria_origen": "x" * 1025}, r"fila 2: libreria_origen excede 1024 caracteres"),
        ({"comentario": "x" * 4097}, r"fila 2: comentario excede 4096 caracteres"),
        ({"comentario": "a\tb"}, r"fila 2: comentario contiene caracteres de control"),
        ({"numero_de_llamadores": "-1"}, r"fila 2: numero_de_llamadores=-1 fuera de rango"),
        ({"numero_de_llamadores": "1000001"}, r"fila 2: numero_de_llamadores=1000001 fuera de rango"),
    ],
)
def test_parsear_rechaza_el_campo_invalido_nombrando_fila_y_campo(
    cambios: dict[str, str], mensaje: str
) -> None:
    with pytest.raises(ValueError, match=mensaje):
        parsear_funciones_csv(csv_funciones([fila(**cambios)]))


def test_parsear_nombra_la_fila_del_error_cuando_no_es_la_primera() -> None:
    texto = csv_funciones([fila(), fila(direccion="0x80014A0C", tamano="0")])
    with pytest.raises(ValueError, match=r"fila 3: tamano=0"):
        parsear_funciones_csv(texto)


def test_parsear_rechaza_filas_con_campos_de_menos() -> None:
    texto = csv_funciones([fila()[:-1]])
    with pytest.raises(ValueError, match=r"fila 2: se esperaban 8 campos"):
        parsear_funciones_csv(texto)


def test_parsear_acota_el_numero_de_filas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lectura, "MAX_FILAS", 2)
    texto = csv_funciones([fila(), fila(direccion="0x80014A0C"), fila(direccion="0x80014A10")])
    with pytest.raises(ValueError, match=r"funciones\.csv: mas de 2 filas"):
        parsear_funciones_csv(texto)


def test_leer_funciones_csv_lee_un_archivo_utf8(tmp_path: Path) -> None:
    ruta = tmp_path / "funciones.csv"
    ruta.write_text(MUESTRA, encoding="utf-8", newline="")
    assert leer_funciones_csv(ruta) == parsear_funciones_csv(MUESTRA)


def test_leer_funciones_csv_rechaza_archivos_demasiado_grandes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ruta = tmp_path / "funciones.csv"
    ruta.write_text(MUESTRA, encoding="utf-8", newline="")
    monkeypatch.setattr(lectura, "MAX_BYTES_CSV", 10)
    with pytest.raises(ValueError, match=r"funciones\.csv: el archivo excede 10 bytes"):
        leer_funciones_csv(ruta)


def test_leer_funciones_csv_rechaza_codificaciones_distintas_de_utf8(tmp_path: Path) -> None:
    ruta = tmp_path / "funciones.csv"
    ruta.write_bytes(b"\xff\xfe\x00\x01")
    with pytest.raises(ValueError, match=r"funciones\.csv: la codificacion no es UTF-8"):
        leer_funciones_csv(ruta)


def test_leer_funciones_csv_propaga_archivo_inexistente(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        leer_funciones_csv(tmp_path / "no_existe.csv")
