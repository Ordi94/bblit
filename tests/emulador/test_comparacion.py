"""Lectura de volcados y archivos para `comparar`, con archivos temporales."""

import pytest
from tools.emulador import comparacion
from tools.emulador.dominio import RAM_TAMANO


@pytest.fixture
def ram(tmp_path):
    datos = bytearray(RAM_TAMANO)
    datos[0x14A00:0x14A10] = bytes(range(16))
    ruta = tmp_path / "ram.bin"
    ruta.write_bytes(datos)
    return ruta


def test_comparar_con_archivo_usa_lo_que_aporta_el_archivo(ram, tmp_path):
    archivo = tmp_path / "exe.bin"
    archivo.write_bytes(b"\xff" * 0x800 + bytes(range(16)))
    resultado = comparacion.comparar_con_archivo(ram, 0x80014A00, archivo, 0x800)
    assert resultado.bytes_comparados == 16
    assert resultado.bytes_distintos == 0
    assert not resultado.tamano_distinto


def test_comparar_con_archivo_reporta_diferencias(ram, tmp_path):
    archivo = tmp_path / "exe.bin"
    archivo.write_bytes(bytes([0, 1, 9, 3]))
    resultado = comparacion.comparar_con_archivo(ram, 0x80014A00, archivo)
    assert (resultado.bytes_iguales, resultado.bytes_distintos, resultado.primer_offset_distinto) == (3, 1, 2)


def test_comparar_con_archivo_con_longitud_explicita_marca_tamano_distinto(ram, tmp_path):
    archivo = tmp_path / "exe.bin"
    archivo.write_bytes(bytes(range(4)))
    resultado = comparacion.comparar_con_archivo(ram, 0x80014A00, archivo, longitud=8)
    assert resultado.bytes_comparados == 4
    assert resultado.longitud_a == 8
    assert resultado.tamano_distinto


def test_comparar_con_archivo_rechaza_offset_pasado_el_final(ram, tmp_path):
    archivo = tmp_path / "exe.bin"
    archivo.write_bytes(b"abc")
    with pytest.raises(ValueError, match="sobrepasa el tamano"):
        comparacion.comparar_con_archivo(ram, 0x80014A00, archivo, 4)


def test_comparar_con_archivo_rechaza_offset_negativo(ram, tmp_path):
    archivo = tmp_path / "exe.bin"
    archivo.write_bytes(b"abc")
    with pytest.raises(ValueError, match="mayor o igual a 0"):
        comparacion.comparar_con_archivo(ram, 0x80014A00, archivo, -1)


def test_comparar_rechaza_volcado_de_otro_tamano(tmp_path):
    corto = tmp_path / "corto.bin"
    corto.write_bytes(bytes(100))
    with pytest.raises(ValueError, match="2097152"):
        comparacion.comparar_con_archivo(corto, 0x80000000, corto)


def test_comparar_volcados_ve_los_cambios(ram, tmp_path):
    otro = bytearray(ram.read_bytes())
    otro[0x14A05] = 0xEE
    ruta_b = tmp_path / "b.bin"
    ruta_b.write_bytes(otro)
    resultado = comparacion.comparar_volcados(ram, ruta_b, 0x80014A00, 32)
    assert (resultado.bytes_comparados, resultado.bytes_distintos, resultado.primer_offset_distinto) == (
        32,
        1,
        5,
    )


def test_comparar_volcados_sin_longitud_cubre_hasta_el_final(ram):
    resultado = comparacion.comparar_volcados(ram, ram, 0x80100000)
    assert resultado.bytes_comparados == 0x100000
    assert resultado.porcentaje_igual == 100.0


def test_comparar_volcados_rechaza_longitud_que_sobrepasa_la_ram(ram):
    with pytest.raises(ValueError, match="sobrepasa"):
        comparacion.comparar_volcados(ram, ram, 0x801FFFF0, 32)
