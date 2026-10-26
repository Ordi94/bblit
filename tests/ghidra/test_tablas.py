import pytest
from tools.ghidra.tablas import (
    Corrida,
    corrida_que_contiene,
    detectar_corridas,
    tramo_de_tabla,
)

from tests.ghidra.segmentos import BASE, segmento

CODIGO = (0x80014AC4, 0x80045DA0)
DATOS = (0x8005DEA0, 0x8005E000)


def test_detecta_corridas_de_punteros_a_codigo_con_el_largo_minimo() -> None:
    datos = segmento(
        {
            0x8005DEA0: 0x80014AC4,
            0x8005DEA4: 0x80014B00,
            0x8005DEA8: 0x00000000,
            0x8005DEAC: 0x80014B00,
            0x8005DEB0: 0x80014B02,
            0x8005DEB4: 0x80045DA0,
            0x8005DFF8: 0x80014B04,
            0x8005DFFC: 0x80014B08,
        }
    )
    corridas = detectar_corridas(datos, BASE, DATOS, CODIGO)
    assert corridas == [
        Corrida(0x8005DEA0, (0x80014AC4, 0x80014B00)),
        Corrida(0x8005DFF8, (0x80014B04, 0x80014B08)),
    ]
    assert corridas[0].fin == 0x8005DEA8
    assert detectar_corridas(datos, BASE, DATOS, CODIGO, minimo=1)[1] == Corrida(0x8005DEAC, (0x80014B00,))


@pytest.mark.parametrize(
    ("rango", "minimo"),
    [
        ((0x8005DEA1, 0x8005DEA8), 2),
        ((0x8005DEA0, 0x8005DEA9), 2),
        ((0x80014000, 0x8005DEA8), 2),
        ((0x8005DEA0, 0x80070000), 2),
        ((0x8005DEA8, 0x8005DEA0), 2),
        (DATOS, 0),
    ],
)
def test_rechaza_rangos_invalidos_y_minimos_menores_que_uno(rango: tuple[int, int], minimo: int) -> None:
    with pytest.raises(ValueError, match="tablas:"):
        detectar_corridas(segmento({}), BASE, rango, CODIGO, minimo)


def test_busca_la_corrida_que_contiene_una_direccion() -> None:
    corridas = [Corrida(0x8005DEA0, (1, 2)), Corrida(0x8005DEB0, (3, 4, 5))]
    assert corrida_que_contiene(corridas, 0x8005DEA0) == corridas[0]
    assert corrida_que_contiene(corridas, 0x8005DEA4) == corridas[0]
    assert corrida_que_contiene(corridas, 0x8005DEA8) is None
    assert corrida_que_contiene(corridas, 0x8005DEB8) == corridas[1]
    assert corrida_que_contiene(corridas, 0x8005DE00) is None
    assert corrida_que_contiene([], 0x8005DEA0) is None


def test_una_tabla_termina_en_la_siguiente_frontera_o_al_acabar_la_corrida() -> None:
    corrida = Corrida(0x8005DEA0, (10, 20, 30, 40))
    assert tramo_de_tabla(corrida, 0x8005DEA0, [0x8005DEA8]) == (10, 20)
    assert tramo_de_tabla(corrida, 0x8005DEA4, [0x8005DEA0, 0x8005DEA8, 0x8005DEAC]) == (20,)
    assert tramo_de_tabla(corrida, 0x8005DEA0, [0x80000000]) == (10, 20, 30, 40)


@pytest.mark.parametrize("direccion", [0x8005DEA2, 0x8005DE9C, 0x8005DEB0])
def test_una_direccion_mal_alineada_o_fuera_de_la_corrida_se_rechaza(direccion: int) -> None:
    with pytest.raises(ValueError, match="alineada y dentro de la corrida"):
        tramo_de_tabla(Corrida(0x8005DEA0, (1, 2, 3, 4)), direccion, [])
