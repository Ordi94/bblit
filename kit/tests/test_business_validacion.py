"""Reglas de los validadores primitivos: listas de admitidos, cotas y mensajes sin filtraciones."""

from pathlib import Path

import pytest
from psxdecomp import validacion as val
from psxdecomp.validacion import ManifiestoError


def test_la_tabla_exigida_debe_ser_un_diccionario() -> None:
    assert val.exigir_tabla({"a": 1}, "rutas") == {"a": 1}
    with pytest.raises(ManifiestoError, match=r"\[rutas\]: se esperaba una tabla"):
        val.exigir_tabla(["a"], "rutas")


def test_una_clave_fuera_de_la_lista_de_admitidas_se_rechaza_sin_volcar_su_valor() -> None:
    with pytest.raises(ManifiestoError) as error:
        val.rechazar_claves_desconocidas({"fuente": "valor-secreto", "src": 1}, {"src"}, "rutas")
    assert "[rutas].fuente" in str(error.value)
    assert "valor-secreto" not in str(error.value)


def test_el_nombre_de_una_clave_desconocida_se_trunca_en_el_mensaje() -> None:
    with pytest.raises(ManifiestoError) as error:
        val.rechazar_claves_desconocidas({"k" * 500: 1}, set(), "rutas")
    assert len(str(error.value)) < 200


def test_con_todas_las_claves_admitidas_no_hay_error() -> None:
    val.rechazar_claves_desconocidas({"a": 1}, {"a", "b"}, "rutas")


def test_una_clave_obligatoria_ausente_se_nombra_en_el_error() -> None:
    with pytest.raises(ManifiestoError, match=r"\[proyecto\]\.nombre: .*falta"):
        val.leer_cadena({}, "nombre", "proyecto", patron=val.PATRON_NOMBRE)


def test_una_cadena_ausente_con_defecto_devuelve_el_defecto() -> None:
    assert val.leer_cadena({}, "x", "s", patron=val.PATRON_NOMBRE, defecto="demo") == "demo"


@pytest.mark.parametrize("valor", [3, "", "con espacio", "a" * 65, "-inicio", "ruta/barra"])
def test_los_nombres_fuera_de_la_lista_de_admitidos_se_rechazan(valor: object) -> None:
    with pytest.raises(ManifiestoError, match=r"\[s\]\.x"):
        val.leer_cadena({"x": valor}, "x", "s", patron=val.PATRON_NOMBRE)


@pytest.mark.parametrize("valor", ["src", "config/splat.yaml", "a.b/c-d_e", "_privada/x"])
def test_las_rutas_relativas_con_caracteres_admitidos_se_aceptan(valor: str) -> None:
    assert val.leer_ruta({"r": valor}, "r", "rutas") == valor


@pytest.mark.parametrize(
    "valor",
    [
        "../fuera",
        "a/../../fuera",
        "a/..",
        "./x",
        "a//b",
        "a/",
        "/absoluta",
        "C:/unidad",
        "a\\b",
        "con espacio",
        "",
        "x" * 201,
        7,
        None,
    ],
)
def test_las_rutas_que_salen_de_la_raiz_o_usan_caracteres_no_admitidos_se_rechazan(valor: object) -> None:
    with pytest.raises(ManifiestoError, match=r"\[rutas\]\.r: se esperaba una ruta relativa"):
        val.leer_ruta({"r": valor}, "r", "rutas")


def test_una_ruta_ausente_sin_defecto_es_obligatoria() -> None:
    with pytest.raises(ManifiestoError, match="falta"):
        val.leer_ruta({}, "r", "rutas")


def test_una_ruta_que_resuelve_fuera_de_la_raiz_se_rechaza(tmp_path: Path) -> None:
    raiz = tmp_path / "proyecto"
    raiz.mkdir()
    val.comprobar_dentro_de_raiz(raiz, "src/interno", "fuentes", "rutas")
    with pytest.raises(ManifiestoError, match="permanezca dentro de la raiz"):
        val.comprobar_dentro_de_raiz(raiz, "../hermano", "fuentes", "rutas")


def test_una_lista_de_rutas_valida_se_devuelve_como_tupla() -> None:
    tabla = {"s": ["a.txt", "b/c.txt"]}
    assert val.leer_lista_rutas(tabla, "s", "rutas", defecto=()) == ("a.txt", "b/c.txt")


def test_una_lista_de_rutas_ausente_usa_el_defecto() -> None:
    assert val.leer_lista_rutas({}, "s", "rutas", defecto=("x.txt",), minimo=1) == ("x.txt",)


@pytest.mark.parametrize(
    "valor",
    ["no-es-lista", [], ["../x"], ["a", "a"], [f"r{i}" for i in range(17)], [3]],
)
def test_las_listas_de_rutas_fuera_de_cotas_o_con_repetidos_se_rechazan(valor: object) -> None:
    with pytest.raises(ManifiestoError, match=r"\[rutas\]\.s"):
        val.leer_lista_rutas({"s": valor}, "s", "rutas", defecto=(), minimo=1)


def test_el_limite_de_elementos_de_una_lista_es_inclusivo() -> None:
    elementos = [f"r{i}" for i in range(val.MAX_ELEMENTOS_LISTA)]
    resultado = val.leer_lista_rutas({"s": elementos}, "s", "rutas", defecto=())
    assert len(resultado) == val.MAX_ELEMENTOS_LISTA


def test_una_lista_de_texto_valida_se_devuelve_como_tupla() -> None:
    tabla = {"p": ["overlay"]}
    resultado = val.leer_lista_texto(tabla, "p", "rutas", patron=val.PATRON_SEGMENTO, defecto=())
    assert resultado == ("overlay",)


@pytest.mark.parametrize("invalido", [["a/b"], [3], ["a", "a"], "texto"])
def test_una_lista_de_texto_exige_que_cada_elemento_cumpla_el_patron(invalido: object) -> None:
    with pytest.raises(ManifiestoError, match=r"\[rutas\]\.p"):
        val.leer_lista_texto({"p": invalido}, "p", "rutas", patron=val.PATRON_SEGMENTO, defecto=())


@pytest.mark.parametrize("valor", [0x80000000, 0x80014AC4, 0x80800000])
def test_las_direcciones_dentro_del_rango_ram_se_aceptan_incluidos_los_extremos(valor: int) -> None:
    assert val.leer_direccion({"d": valor}, "d", "zonas") == valor


@pytest.mark.parametrize("valor", [0x7FFFFFFF, 0x80800001, 0, -1, True, 1.5, "0x80010000", None])
def test_las_direcciones_fuera_de_rango_o_de_otro_tipo_se_rechazan(valor: object) -> None:
    with pytest.raises(ManifiestoError, match=r"\[zonas\]\.d: se esperaba un entero entre 0x80000000"):
        val.leer_direccion({"d": valor}, "d", "zonas")


def test_una_direccion_ausente_es_obligatoria() -> None:
    with pytest.raises(ManifiestoError, match="falta"):
        val.leer_direccion({}, "d", "zonas")


def test_una_expresion_valida_se_conserva_tal_cual() -> None:
    assert val.leer_regex({"e": r"_\d+$"}, "e", "convenciones", defecto="x") == r"_\d+$"
    assert val.leer_regex({}, "e", "convenciones", defecto="x") == "x"


@pytest.mark.parametrize("valor", ["(sin cerrar", "[", "*inicio", "", "a" * 201, 5, None])
def test_las_expresiones_invalidas_o_fuera_de_cota_se_rechazan(valor: object) -> None:
    with pytest.raises(ManifiestoError, match=r"\[convenciones\]\.e: se esperaba una expresion regular"):
        val.leer_regex({"e": valor}, "e", "convenciones", defecto="x")


def test_la_expresion_con_el_numero_de_grupos_pedido_se_acepta() -> None:
    assert val.leer_regex({"e": "(a)"}, "e", "c", defecto="(x)", grupos=1) == "(a)"


@pytest.mark.parametrize("expresion", ["a", "(a)(b)"])
def test_la_expresion_con_otro_numero_de_grupos_se_rechaza(expresion: str) -> None:
    with pytest.raises(ManifiestoError, match="1 grupo"):
        val.leer_regex({"e": expresion}, "e", "c", defecto="(x)", grupos=1)
