from tools.ghidra.depuracion import refinar_con_tablas
from tools.ghidra.dominio import Funcion

from tests.ghidra.ensamblaje import NOP, RA, V0, addiu, beq, bne, j, jr, programa, retorno
from tests.ghidra.segmentos import segmento
from tests.ghidra.sintetica import funcion

M = 0x80020000
"""Inicio del bloque madre de las pruebas (dentro del rango del juego)."""


def _bloque(tamano: int = 40) -> Funcion:
    return funcion(M, "FUN_80020000", tamano)


def _rutinas(cantidad: int) -> dict[int, int]:
    palabras: list[int] = []
    for _ in range(cantidad):
        palabras += retorno()
    return programa(M, palabras)


def _tamanos(funciones: list[Funcion]) -> list[tuple[int, int]]:
    return [(f.direccion, f.tamano) for f in funciones]


def test_cada_destino_de_una_tabla_de_punteros_parte_el_bloque_en_rutinas_exactas() -> None:
    destinos = {M + 8, M + 16, M + 24, M + 32}
    refinado = refinar_con_tablas([_bloque()], segmento(_rutinas(5)), destinos, set())
    assert _tamanos(refinado.funciones) == [(M + 8 * i, 8) for i in range(5)]
    assert refinado.nuevas == [(M + 8, M), (M + 16, M), (M + 24, M), (M + 32, M)]
    assert refinado.conflictos == []
    assert refinado.fusionadas == []
    assert refinado.funciones[1].nombre == "FUN_80020008"
    assert refinado.funciones[0].nombre == "FUN_80020000"


def test_las_entradas_repetidas_y_los_destinos_que_ya_son_funcion_no_crean_nada() -> None:
    funciones = [funcion(M, "FUN_80020000", 16), funcion(M + 16, "FUN_80020010", 24)]
    refinado = refinar_con_tablas(funciones, segmento(_rutinas(5)), [M + 16, M + 16, M + 24, M + 24], set())
    assert _tamanos(refinado.funciones) == [(M, 16), (M + 16, 8), (M + 24, 16)]
    assert refinado.nuevas == [(M + 24, M + 16)]


def test_los_destinos_invalidos_se_reportan_sin_partir_nada() -> None:
    refinado = refinar_con_tablas(
        [_bloque()], segmento(_rutinas(5)), [0x80001000, M + 10, 0x80030000, 0x8004E000], set()
    )
    assert _tamanos(refinado.funciones) == [(M, 40)]
    assert refinado.conflictos == [
        (0x80001000, "fuera del rango del juego"),
        (M + 10, "destino desalineado"),
        (0x80030000, "ninguna funcion lo contiene"),
        (0x8004E000, "fuera del rango del juego"),
    ]


def test_un_destino_cuya_pieza_no_cierra_como_funcion_no_se_aplica() -> None:
    palabras = programa(M, [jr(RA), NOP, addiu(V0, 0, 1), addiu(V0, 0, 2), jr(RA), NOP])
    refinado = refinar_con_tablas(
        [funcion(M, "FUN_80020000", 24)], segmento(palabras), [M + 12, M + 8], set()
    )
    assert _tamanos(refinado.funciones) == [(M, 8), (M + 8, 16)]
    assert refinado.conflictos == [(M + 12, "la pieza anterior o la siguiente no cierra como funcion")]
    assert refinado.nuevas == [(M + 8, M)]


def _par(origen: list[int], destino: list[int], tamano: int = 32) -> tuple[list[Funcion], bytes]:
    base = 0x80021000
    funciones = [funcion(base, "FUN_80021000", tamano), funcion(base + tamano, "FUN_80021020", tamano)]
    palabras = programa(base, origen) | programa(base + tamano, destino)
    return funciones, segmento(palabras)


_CUERPO = [*retorno(), *retorno(), *retorno(), *retorno()]


def test_una_funcion_a_la_que_la_anterior_bifurca_con_ramas_condicionales_es_continuacion() -> None:
    base = 0x80021000
    origen = [beq(0, V0, base, base + 0x28), NOP, *_CUERPO[2:]]
    funciones, datos = _par(origen, _CUERPO)
    refinado = refinar_con_tablas(funciones, datos, set(), set())
    assert _tamanos(refinado.funciones) == [(base, 64)]
    assert refinado.fusionadas == [(base + 32, base)]


def test_un_j_al_interior_cuenta_pero_un_j_al_inicio_es_una_llamada_de_cola() -> None:
    base = 0x80021000
    interior, datos = _par([j(base + 0x28), NOP, *_CUERPO[2:]], _CUERPO)
    cola, datos_cola = _par([j(base + 0x20), NOP, *_CUERPO[2:]], _CUERPO)
    assert refinar_con_tablas(interior, datos, set(), set()).fusionadas == [(base + 32, base)]
    assert refinar_con_tablas(cola, datos_cola, set(), set()).fusionadas == []


def test_el_destino_de_una_tabla_de_salto_sin_llamadores_es_continuacion() -> None:
    funciones, datos = _par(_CUERPO, _CUERPO)
    assert refinar_con_tablas(funciones, datos, set(), {0x80021020}).fusionadas == [(0x80021020, 0x80021000)]
    assert refinar_con_tablas(funciones, datos, set(), set()).fusionadas == []


def test_una_funcion_que_alguien_llama_no_es_continuacion() -> None:
    base = 0x80021000
    funciones, datos = _par(_CUERPO, _CUERPO)
    llamada = 0x0C000000 | (0x80021020 >> 2) & 0x03FFFFFF
    con_jal = datos + b""  # el segmento es inmutable: se reconstruye con la llamada
    palabras = programa(base, _CUERPO) | programa(base + 32, _CUERPO) | {0x80022000: llamada}
    con_jal = segmento(palabras)
    assert refinar_con_tablas(funciones, con_jal, set(), {0x80021020}).fusionadas == []
    assert refinar_con_tablas(funciones, datos, [0x80021020], {0x80021020}).fusionadas == []


def test_la_fusion_solo_aplica_al_codigo_del_juego_y_a_funciones_contiguas() -> None:
    fuera = [funcion(0x80010000 + 0x4A00, "FUN_80014A00", 32), funcion(0x80014A20, "FUN_80014A20", 32)]
    datos = segmento(programa(0x80014A00, _CUERPO) | programa(0x80014A20, _CUERPO))
    assert refinar_con_tablas(fuera, datos, set(), {0x80014A20}).fusionadas == []
    separadas = [funcion(0x80021000, "FUN_80021000", 32), funcion(0x80021040, "FUN_80021040", 32)]
    assert refinar_con_tablas(separadas, datos, set(), {0x80021040}).fusionadas == []
    assert refinar_con_tablas([], datos, set(), set()).funciones == []


F1 = 0x80021000
F2 = 0x80021040
PROLOGO = 0x27BDFFE0
"""``addiu sp, sp, -0x20``."""


def _rellenar(palabras: list[int], tamano: int) -> list[int]:
    """Completa con ``nop`` y cierra con ``jr ra`` y su ranura, hasta ``tamano`` bytes."""
    return [*palabras, *([NOP] * (tamano // 4 - len(palabras) - 2)), *retorno()]


def _funcion_partida(
    *, segunda_con_prologo: bool, bifurca_a_la_segunda: bool, llamada: bool
) -> tuple[list[Funcion], bytes]:
    """Una funcion grande cortada en dos: la primera bifurca a la segunda, que vuelve con rama y ``j``."""
    primera = [PROLOGO, NOP]
    if bifurca_a_la_segunda:
        primera = [PROLOGO, beq(0, V0, F1 + 4, F2 + 0x10), NOP, bne(V0, 0, F1 + 12, F2 + 0x18), NOP]
    segunda = [PROLOGO] if segunda_con_prologo else [0x92420000]
    segunda += [bne(V0, 0, F2 + 4, F1 + 8), NOP, j(F1 + 0x10), NOP]
    palabras = programa(F1, _rellenar(primera, 0x40)) | programa(F2, _rellenar(segunda, 0x40))
    if llamada:
        palabras[0x80022000] = 0x0C000000 | (F2 >> 2) & 0x03FFFFFF
    return [funcion(F1, "FUN_80021000", 0x40), funcion(F2, "FUN_80021040", 0x40)], segmento(palabras)


def test_una_funcion_partida_con_ramas_cruzadas_sin_prologo_ni_llamadas_se_une_con_el_tamano_sumado() -> None:
    funciones, datos = _funcion_partida(segunda_con_prologo=False, bifurca_a_la_segunda=True, llamada=False)
    refinado = refinar_con_tablas(funciones, datos, set(), set())
    assert _tamanos(refinado.funciones) == [(F1, 0x80)]
    assert refinado.fusionadas == [(F2, F1)]


def test_la_segunda_mitad_se_conserva_si_alguien_la_llama_o_si_nadie_bifurca_a_ella() -> None:
    llamada = _funcion_partida(segunda_con_prologo=True, bifurca_a_la_segunda=True, llamada=True)
    aislada = _funcion_partida(segunda_con_prologo=True, bifurca_a_la_segunda=False, llamada=False)
    for funciones, datos in (llamada, aislada):
        refinado = refinar_con_tablas(funciones, datos, set(), set())
        assert _tamanos(refinado.funciones) == [(F1, 0x40), (F2, 0x40)]
        assert refinado.fusionadas == []
