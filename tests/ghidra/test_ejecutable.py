from pathlib import Path

import pytest
from tools.ghidra.dominio import DIRECCION_BASE, DIRECCION_FIN
from tools.ghidra.ejecutable import instruccion_valida, leer_segmento, palabra_en

from tests.ghidra.segmentos import DATO, INSTRUCCION, JR_RA, escribir_ejecutable, segmento


def test_leer_segmento_devuelve_el_cuerpo_sin_la_cabecera(tmp_path: Path) -> None:
    ruta = escribir_ejecutable(tmp_path / "SLUS_008.38", {0x80014A04: 0x11223344})
    datos = leer_segmento(ruta)
    assert len(datos) == 0x55000
    assert datos[4:8] == bytes([0x44, 0x33, 0x22, 0x11])


def test_leer_segmento_rechaza_un_tamano_inesperado(tmp_path: Path) -> None:
    ruta = tmp_path / "x"
    ruta.write_bytes(b"PS-X EXE" + bytes(100))
    with pytest.raises(ValueError, match=r"ejecutable: el tamano debe ser 350208 bytes"):
        leer_segmento(ruta)


def test_leer_segmento_exige_la_firma_psx(tmp_path: Path) -> None:
    ruta = tmp_path / "x"
    ruta.write_bytes(bytes(0x800 + 0x55000))
    with pytest.raises(ValueError, match=r"ejecutable: falta la firma PS-X EXE"):
        leer_segmento(ruta)


def test_leer_segmento_propaga_archivo_inexistente(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        leer_segmento(tmp_path / "no_existe")


def test_palabra_en_lee_little_endian() -> None:
    datos = segmento({0x80014A08: JR_RA, DIRECCION_FIN - 4: 0xAABBCCDD})
    assert palabra_en(datos, 0x80014A08) == 0x03E00008
    assert palabra_en(datos, DIRECCION_FIN - 4) == 0xAABBCCDD
    assert palabra_en(datos, DIRECCION_BASE) == 0


@pytest.mark.parametrize("direccion", [DIRECCION_BASE - 4, DIRECCION_FIN, DIRECCION_BASE + 2])
def test_palabra_en_rechaza_direcciones_fuera_del_segmento_o_desalineadas(direccion: int) -> None:
    with pytest.raises(ValueError, match=rf"direccion 0x{direccion:08X} fuera del segmento o no alineada"):
        palabra_en(segmento({}), direccion)


def test_palabra_en_rechaza_un_segmento_de_otro_tamano() -> None:
    with pytest.raises(ValueError, match=r"segmento: el tamano debe ser 348160 bytes"):
        palabra_en(bytes(8), DIRECCION_BASE)


def test_instruccion_valida_distingue_codigo_de_datos() -> None:
    assert instruccion_valida(JR_RA, DIRECCION_BASE) is True
    assert instruccion_valida(INSTRUCCION, DIRECCION_BASE) is True
    assert instruccion_valida(DATO, DIRECCION_BASE) is False
