import pytest
from tools.ghidra import simbolos as modulo
from tools.ghidra.dominio import Simbolo
from tools.ghidra.simbolos import formatear_simbolo, formatear_tabla, parsear_tabla

TABLA = (
    "__main = 0x80014A00; // type:func size:0x8\n"
    "main = 0x80016414; // type:func size:0x7F8\n"
    "func_80016C0C = 0x80016C0C; // type:func size:0x64\n"
)

SIMBOLOS = [
    Simbolo("__main", 0x80014A00, "func", 0x8),
    Simbolo("main", 0x80016414, "func", 0x7F8),
    Simbolo("func_80016C0C", 0x80016C0C, "func", 0x64),
]


def test_formatear_simbolo_usa_hexadecimal_en_mayusculas() -> None:
    linea = formatear_simbolo(Simbolo("DrawSync", 0x80051938, "func", 0x68))
    assert linea == "DrawSync = 0x80051938; // type:func size:0x68"


def test_formatear_simbolo_de_datos() -> None:
    linea = formatear_simbolo(Simbolo("D_80060000", 0x80060000, "data", 0xA0))
    assert linea == "D_80060000 = 0x80060000; // type:data size:0xA0"


def test_formatear_tabla_escribe_una_linea_por_simbolo_con_salto_final() -> None:
    assert formatear_tabla(SIMBOLOS) == TABLA


def test_formatear_tabla_vacia_es_texto_vacio() -> None:
    assert formatear_tabla([]) == ""


def test_formatear_tabla_valida_antes_de_escribir() -> None:
    with pytest.raises(ValueError, match=r"simbolo a: se solapa con b"):
        formatear_tabla([Simbolo("a", 0x80014A00, "func", 0x10), Simbolo("b", 0x80014A08, "func", 4)])


def test_parsear_tabla_recupera_los_simbolos_exactos() -> None:
    assert parsear_tabla(TABLA) == SIMBOLOS


def test_parsear_tabla_vacia() -> None:
    assert parsear_tabla("") == []


def test_ida_y_vuelta_conserva_la_tabla() -> None:
    assert formatear_tabla(parsear_tabla(TABLA)) == TABLA


@pytest.mark.parametrize(
    ("linea", "numero"),
    [
        ("main = 0x80016414; // type:func size:0x7F8 ", 2),
        ("main = 0x80016414 // type:func size:0x7F8", 2),
        ("main = 0x80016414; // type:code size:0x7F8", 2),
        ("main = 0x8001641; // type:func size:0x7F8", 2),
        ("main = 0x8001641a; // type:func size:0x7F8", 2),
        ("main  = 0x80016414; // type:func size:0x7F8", 2),
        ("1main = 0x80016414; // type:func size:0x7F8", 2),
        ("", 2),
    ],
)
def test_parsear_tabla_rechaza_lineas_con_formato_invalido_indicando_el_numero(
    linea: str, numero: int
) -> None:
    texto = "__main = 0x80014A00; // type:func size:0x8\n" + linea + "\n"
    with pytest.raises(ValueError, match=rf"symbols linea {numero}: formato invalido"):
        parsear_tabla(texto)


def test_parsear_tabla_valida_el_contrato_tras_leer() -> None:
    texto = "b = 0x80014A10; // type:func size:0x4\na = 0x80014A00; // type:func size:0x4\n"
    with pytest.raises(ValueError, match=r"simbolo a: fuera de orden ascendente tras b"):
        parsear_tabla(texto)


def test_parsear_tabla_acota_el_numero_de_lineas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(modulo, "MAX_LINEAS", 2)
    with pytest.raises(ValueError, match=r"symbols: 3 lineas exceden el maximo de 2"):
        parsear_tabla("a\nb\nc\n")
