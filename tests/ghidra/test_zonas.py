import pytest
from tools.ghidra.zonas import FIN_JUEGO, INICIO_JUEGO, clasificar_zona, region_de_dato


@pytest.mark.parametrize(
    ("direccion", "clase"),
    [
        (0x80010204, "externo"),
        (0x80014A00, "arranque"),
        (INICIO_JUEGO - 4, "arranque"),
        (INICIO_JUEGO, "juego"),
        (FIN_JUEGO - 4, "juego"),
        (FIN_JUEGO, "libreria"),
        (0x8005DE9C, "libreria"),
        (0x8005DEA0, "externo"),
    ],
)
def test_clasifica_las_direcciones_de_codigo_por_zona(direccion: int, clase: str) -> None:
    assert clasificar_zona(direccion) == clase


@pytest.mark.parametrize(
    ("direccion", "region"),
    [
        (0x1F800010, "scratchpad"),
        (0x1F801810, "hardware"),
        (0x80010000, "estado_global"),
        (0x80020000, "codigo_y_literales"),
        (0x8005E35C, "datos_y_tablas"),
        (0x80067C7C, "cadenas_y_mensajes"),
        (0x80069330, "datos_pequenos"),
        (0x8006CF68, "bss"),
        (0x80077000, "heap"),
        (0x00001000, "otra"),
    ],
)
def test_clasifica_los_datos_por_region(direccion: int, region: str) -> None:
    assert region_de_dato(direccion) == region
