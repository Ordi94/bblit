"""Reglas puras del dominio: RAM, direcciones, comparacion y huella del ejecutable."""

import pytest
from tools.emulador import dominio

from tests.emulador import sintetica


def test_validar_ram_acepta_el_tamano_exacto():
    datos = bytes(dominio.RAM_TAMANO)
    assert dominio.validar_ram(datos) is datos


@pytest.mark.parametrize("tamano", [0, dominio.RAM_TAMANO - 1, dominio.RAM_TAMANO + 1])
def test_validar_ram_rechaza_otros_tamanos(tamano):
    with pytest.raises(ValueError, match="2097152"):
        dominio.validar_ram(bytes(tamano))


def test_offset_de_ram_traduce_direcciones():
    assert dominio.offset_de_ram(0x80000000) == 0
    assert dominio.offset_de_ram(0x80014A00) == 0x14A00
    assert dominio.offset_de_ram(0x801FFFFF, 1) == 0x1FFFFF


@pytest.mark.parametrize("direccion", [0x7FFFFFFF, 0x80200000, 0, 0xFFFFFFFF])
def test_offset_de_ram_rechaza_direcciones_fuera_de_la_ram(direccion):
    with pytest.raises(ValueError, match="direccion"):
        dominio.offset_de_ram(direccion)


def test_offset_de_ram_rechaza_regiones_que_sobrepasan_el_final():
    with pytest.raises(ValueError, match="sobrepasa"):
        dominio.offset_de_ram(0x801FFFFF, 2)


def test_offset_de_ram_rechaza_longitud_negativa():
    with pytest.raises(ValueError, match="longitud"):
        dominio.offset_de_ram(0x80000000, -1)


def test_comparar_regiones_iguales():
    resultado = dominio.comparar_regiones(0x80000000, b"abcd", b"abcd")
    assert (resultado.bytes_iguales, resultado.bytes_distintos) == (4, 0)
    assert resultado.primer_offset_distinto is None
    assert resultado.porcentaje_igual == 100.0
    assert not resultado.tamano_distinto


def test_comparar_regiones_reporta_el_primer_offset_distinto():
    resultado = dominio.comparar_regiones(0x80000000, b"abXd", b"abcY")
    assert (resultado.bytes_iguales, resultado.bytes_distintos) == (2, 2)
    assert resultado.primer_offset_distinto == 2
    assert resultado.porcentaje_igual == 50.0


def test_comparar_regiones_de_distinto_tamano_compara_el_minimo():
    resultado = dominio.comparar_regiones(0x80000000, b"abc", b"abcdef")
    assert resultado.bytes_comparados == 3
    assert (resultado.longitud_a, resultado.longitud_b) == (3, 6)
    assert resultado.tamano_distinto


def test_comparar_regiones_vacias_dan_cien_por_ciento():
    assert dominio.comparar_regiones(0x80000000, b"", b"x").porcentaje_igual == 100.0


def test_comparar_regiones_rechaza_direccion_fuera_de_la_ram():
    with pytest.raises(ValueError, match="direccion"):
        dominio.comparar_regiones(0x1000, b"a", b"a")


def test_a_json_usa_camel_case():
    claves = dominio.comparar_regiones(0x80014A00, b"ab", b"aX").a_json()
    assert claves == {
        "direccion": "0x80014A00",
        "bytesComparados": 2,
        "bytesIguales": 1,
        "bytesDistintos": 1,
        "primerOffsetDistinto": 1,
        "porcentajeIgual": 50.0,
        "longitudA": 2,
        "longitudB": 2,
        "tamanoDistinto": False,
    }


def test_prefijo_de_ejecutable_devuelve_direccion_y_huella():
    exe = sintetica.ejecutable_psx(0x80014A00)
    direccion, huella = dominio.prefijo_de_ejecutable(exe)
    assert direccion == 0x80014A00
    assert huella == exe[0x800:0x900]


def test_prefijo_de_ejecutable_rechaza_firma_incorrecta():
    with pytest.raises(ValueError, match="PS-X EXE"):
        dominio.prefijo_de_ejecutable(bytes(0x1000))


def test_prefijo_de_ejecutable_rechaza_archivos_cortos():
    with pytest.raises(ValueError, match="al menos"):
        dominio.prefijo_de_ejecutable(sintetica.ejecutable_psx()[:0x850])


def test_prefijo_de_ejecutable_rechaza_direccion_de_carga_fuera_de_la_ram():
    with pytest.raises(ValueError, match="direccion"):
        dominio.prefijo_de_ejecutable(sintetica.ejecutable_psx(0x10000000))
