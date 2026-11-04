"""Casos limite del permutador: entradas que los analizadores deben tolerar sin perder el resto."""

from types import SimpleNamespace

import pytest
from psxdecomp.permutador import analisis as an
from psxdecomp.permutador import c
from psxdecomp.permutador import mutaciones as mut

from .test_business_permutar_mutaciones import CABECERA, TIPOS


def test_un_declarador_vacio_no_aporta_nombre_a_un_typedef() -> None:
    assert an._declarados_por("typedef int a,") == ["a"]


def test_un_declarador_que_no_es_identificador_se_ignora() -> None:
    assert an._declaradores("*a, 3") == [(1, "a", False)]


def test_una_palabra_reservada_al_inicio_de_linea_no_es_una_global() -> None:
    tabla = an.construir_tabla(["return x;\ns32 contador;"])
    assert "x" not in tabla.globales
    assert "contador" in tabla.globales


def test_una_declaracion_sin_inicial_no_lee_ni_escribe_nada() -> None:
    funcion = c.analizar_funcion("void f(void)\n{\n    s32 a;\n}", "f")
    efectos = an.efectos_profundos(funcion.cuerpo)
    assert not efectos.barrera


def test_dos_comentarios_seguidos_se_acumulan_como_previos_del_mismo_token() -> None:
    tokens = c.tokenizar("/* a */ /* b */ x")
    assert tokens[0].texto == "x"
    assert len(tokens[0].previos) == 2


def test_reemplazar_un_hijo_ausente_recorre_las_listas_y_devuelve_falso() -> None:
    ausente = c.Num("9")
    padre = SimpleNamespace(escalar=c.Num("3"), lista=[c.Num("1"), c.Num("2")])
    assert c.reemplazar_hijo(padre, ausente, c.Num("0")) is False
    assert [x.texto for x in padre.lista] == ["1", "2"]


def test_los_bloques_anidados_se_recorren_una_sola_vez() -> None:
    funcion = c.analizar_funcion("void f(void)\n{\n    {\n        {\n        }\n    }\n}", "f")
    assert len(list(c.todos_los_bloques(funcion.cuerpo))) == 3


def test_quitar_una_declaracion_inexistente_no_toca_la_funcion() -> None:
    funcion = c.analizar_funcion("void f(void)\n{\n    s32 a;\n    a = 1;\n}", "f")
    antes = c.imprimir_funcion(funcion)
    mut._quitar_declaracion(funcion, "inexistente")
    assert c.imprimir_funcion(funcion) == antes


def test_el_tope_de_vecinos_por_mutacion_corta_la_enumeracion(monkeypatch: pytest.MonkeyPatch) -> None:
    funcion = c.analizar_funcion(
        "void f(Objeto* o, s32 x, s32 y)\n{\n    o->valor = x;\n    o->radio = y;\n    x = 1;\n    y = 2;\n}",
        "f",
        TIPOS,
    )
    tabla = an.construir_tabla([CABECERA])
    completos = len(list(mut.vecinos(funcion, tabla)))
    monkeypatch.setattr(mut, "MAX_VECINOS_POR_MUTACION", 1)
    acotados = len(list(mut.vecinos(funcion, tabla)))
    assert 0 < acotados < completos
