import pytest
from tools.ghidra import nombres
from tools.ghidra.dominio import Funcion, Simbolo, construir_simbolos
from tools.ghidra.nombres import Choque, aplicar_nombres, parsear_nombres

from tests.ghidra.sintetica import funcion

A, B, C = 0x80020000, 0x80020008, 0x80020010


def test_el_archivo_se_lee_sin_comentarios_ni_lineas_vacias() -> None:
    texto = "# cabecera\n\n0x8002fa38 CondCiseq  # origen: version PC\n  0x80020000   Otra\n   # sangrado\n"
    assert parsear_nombres(texto) == {0x8002FA38: "CondCiseq", 0x80020000: "Otra"}


@pytest.mark.parametrize(
    ("texto", "mensaje"),
    [
        ("8002FA38 CondCiseq\n", "linea 1: formato invalido"),
        ("0x8002FA3 CondCiseq\n", "linea 1: formato invalido"),
        ("0x8002FA38\n", "linea 1: formato invalido"),
        ("0x8002FA38 dos palabras\n", "linea 1: formato invalido"),
        ("# c\n0x8002FA38 1Cond\n", "linea 2: '1Cond' no es un identificador C valido"),
        ("0x8002FA38 " + "A" * 200 + "\n", "no es un identificador C valido"),
        ("0x8002FA38 A\n0x8002FA38 B\n", "linea 2: la direccion 0x8002FA38 esta repetida"),
        ("0x8002FA38 A\n0x8002FA3C A\n", "linea 2: el nombre A esta repetido"),
    ],
)
def test_las_lineas_invalidas_se_rechazan_nombrando_la_linea(texto: str, mensaje: str) -> None:
    with pytest.raises(ValueError, match=mensaje):
        parsear_nombres(texto)


def test_el_archivo_tiene_una_cota_de_lineas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nombres, "MAX_LINEAS_NOMBRES", 2)
    with pytest.raises(ValueError, match="mas de 2 lineas"):
        parsear_nombres("#\n#\n#\n")


def _tres() -> list[Funcion]:
    return [funcion(A, "FUN_80020000", 8), funcion(B, "FUN_80020008", 8), funcion(C, "FUN_80020010", 8)]


def _aplicar(funciones: list[Funcion], nombres: dict[int, str]) -> tuple[list[Simbolo], list[Choque]]:
    return aplicar_nombres(construir_simbolos(funciones), funciones, nombres)


def test_el_nombre_del_archivo_se_aplica_a_la_funcion_de_esa_direccion() -> None:
    resultado, choques = _aplicar(_tres(), {B: "CondCiseq"})
    assert resultado == [
        Simbolo("func_80020000", A, "func", 8),
        Simbolo("CondCiseq", B, "func", 8),
        Simbolo("func_80020010", C, "func", 8),
    ]
    assert choques == []


def test_un_nombre_oficial_por_firma_nunca_se_pisa_y_el_choque_se_reporta() -> None:
    funciones = [
        funcion(A, "DrawSync", 8, es_libreria=True, nombre_oficial=True),
        funcion(B, "FUN_80020008", 8),
    ]
    resultado, choques = _aplicar(funciones, {A: "OtroNombre"})
    assert resultado[0].nombre == "DrawSync"
    assert choques == [Choque(A, "OtroNombre", "firma", "DrawSync")]


def test_main_tambien_conserva_su_nombre() -> None:
    resultado, choques = _aplicar([funcion(A, "main", 8)], {A: "Principal"})
    assert (resultado[0].nombre, choques) == ("main", [Choque(A, "Principal", "firma", "main")])


def test_si_el_archivo_repite_el_nombre_de_la_firma_no_hay_choque() -> None:
    funciones = [funcion(A, "DrawSync", 8, es_libreria=True, nombre_oficial=True)]
    resultado, choques = _aplicar(funciones, {A: "DrawSync"})
    assert ([s.nombre for s in resultado], choques) == (["DrawSync"], [])


def test_un_nombre_que_ya_usa_otro_simbolo_no_se_aplica() -> None:
    funciones = [
        funcion(A, "DrawSync", 8, es_libreria=True, nombre_oficial=True),
        funcion(B, "FUN_80020008", 8),
        funcion(C, "FUN_80020010", 8),
    ]
    resultado, choques = _aplicar(funciones, {B: "DrawSync", C: "func_80020008"})
    assert [s.nombre for s in resultado] == ["DrawSync", "func_80020008", "func_80020010"]
    assert choques == [
        Choque(B, "DrawSync", "repetido", f"0x{A:08X}"),
        Choque(C, "func_80020008", "repetido", f"0x{B:08X}"),
    ]


def test_una_direccion_que_no_es_inicio_de_funcion_se_reporta() -> None:
    resultado, choques = _aplicar(_tres(), {0x80020004: "Interior"})
    assert [s.nombre for s in resultado] == ["func_80020000", "func_80020008", "func_80020010"]
    assert choques == [Choque(0x80020004, "Interior", "sin funcion", "")]


def test_dos_direcciones_que_piden_el_mismo_nombre_nuevo_solo_la_primera_lo_recibe() -> None:
    resultado, choques = _aplicar(_tres(), {A: "Nuevo", B: "Nuevo"})
    assert [s.nombre for s in resultado] == ["Nuevo", "func_80020008", "func_80020010"]
    assert choques == [Choque(B, "Nuevo", "repetido", f"0x{A:08X}")]
