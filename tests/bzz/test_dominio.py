"""Pruebas de la cabecera: caso valido y cada rechazo con su mensaje exacto."""

import struct

import pytest
from tools.bzz.dominio import (
    Cabecera,
    Seccion,
    calcular_suma_control,
    leer_cabecera,
    nombre_archivo_seccion,
    validar_consumo,
)

from tests.bzz.ayudantes import construir_bzz, flujo_literales, suma_control


def _contenedor_valido() -> bytes:
    return construir_bzz(
        [
            (1, flujo_literales(b"abc")),
            (3, flujo_literales(bytes(2049))),
            (4, flujo_literales(b"z")),
        ],
    )


def _con_entrada(datos: bytes, indice: int, tipo: int, tamano: int, alineado: int) -> bytes:
    """Reemplaza una entrada de la tabla y recalcula la suma de control."""
    editable = bytearray(datos)
    struct.pack_into("<III", editable, 8 + 12 * indice, tipo, tamano, alineado)
    struct.pack_into("<I", editable, 0x7FC, suma_control(bytes(editable)))
    return bytes(editable)


def test_cabecera_valida_construida_a_mano() -> None:
    cabecera = leer_cabecera(_contenedor_valido())
    assert cabecera == Cabecera(
        version=1,
        secciones=(
            Seccion(indice=0, tipo=1, offset=0x800, tamano=8, tamano_alineado=0x800),
            Seccion(indice=1, tipo=3, offset=0x1000, tamano=2310, tamano_alineado=0x1000),
            Seccion(indice=2, tipo=4, offset=0x2000, tamano=6, tamano_alineado=0x800),
        ),
    )


def test_archivo_menor_a_un_sector_se_rechaza() -> None:
    with pytest.raises(ValueError) as error:
        leer_cabecera(bytes(0x7FF))
    assert str(error.value) == "archivo demasiado corto: se esperaban al menos 2048 bytes"


def test_version_distinta_de_uno_se_rechaza() -> None:
    datos = bytearray(_contenedor_valido())
    struct.pack_into("<I", datos, 0, 2)
    with pytest.raises(ValueError) as error:
        leer_cabecera(bytes(datos))
    assert str(error.value) == "version=2 no soportada, se esperaba 1"


@pytest.mark.parametrize("cantidad", [0, 65, 0xFFFFFFFF])
def test_numero_de_secciones_fuera_de_rango_se_rechaza(cantidad: int) -> None:
    datos = bytearray(_contenedor_valido())
    struct.pack_into("<I", datos, 4, cantidad)
    with pytest.raises(ValueError) as error:
        leer_cabecera(bytes(datos))
    assert str(error.value) == f"n_secciones={cantidad} fuera de rango 1..64"


@pytest.mark.parametrize("tipo", [0, 11, 0xFFFFFFFF])
def test_tipo_no_admitido_se_rechaza(tipo: int) -> None:
    datos = _con_entrada(_contenedor_valido(), 0, tipo, 9, 0x800)
    with pytest.raises(ValueError) as error:
        leer_cabecera(datos)
    assert str(error.value) == f"secciones[0].tipo={tipo} no admitido, se esperaba 1..10"


def test_tamano_cero_se_rechaza() -> None:
    datos = _con_entrada(_contenedor_valido(), 0, 1, 0, 0x800)
    with pytest.raises(ValueError) as error:
        leer_cabecera(datos)
    assert str(error.value) == "secciones[0].tamano=0 invalido, se esperaba al menos 1"


def test_tamano_mayor_que_el_alineado_se_rechaza() -> None:
    datos = _con_entrada(_contenedor_valido(), 0, 1, 0x900, 0x800)
    with pytest.raises(ValueError) as error:
        leer_cabecera(datos)
    assert str(error.value) == "secciones[0].tamano=2304 excede tamano_alineado=2048"


def test_tamano_alineado_que_no_es_multiplo_de_sector_se_rechaza() -> None:
    datos = _con_entrada(_contenedor_valido(), 0, 1, 9, 0x801)
    with pytest.raises(ValueError) as error:
        leer_cabecera(datos)
    assert str(error.value) == "secciones[0].tamano_alineado=2049 no es multiplo de 2048"


def test_tamano_alineado_mayor_al_necesario_se_rechaza() -> None:
    datos = _con_entrada(_contenedor_valido(), 0, 1, 9, 0x1000)
    with pytest.raises(ValueError) as error:
        leer_cabecera(datos)
    assert str(error.value) == (
        "secciones[0].tamano_alineado=4096 no es el menor multiplo de 2048 que contiene tamano=9"
    )


def test_suma_de_tamanos_distinta_del_archivo_se_rechaza() -> None:
    with pytest.raises(ValueError) as error:
        leer_cabecera(_contenedor_valido() + bytes(0x800))
    assert (
        str(error.value) == "suma de tamano_alineado mas cabecera=10240 distinta del tamano del archivo=12288"
    )


def test_archivo_truncado_en_la_ultima_seccion_se_rechaza() -> None:
    with pytest.raises(ValueError) as error:
        leer_cabecera(_contenedor_valido()[:-1])
    assert (
        str(error.value) == "suma de tamano_alineado mas cabecera=10240 distinta del tamano del archivo=10239"
    )


def test_suma_de_control_incorrecta_se_rechaza() -> None:
    datos = bytearray(_contenedor_valido())
    datos[0x7FC] ^= 0xFF
    with pytest.raises(ValueError, match=r"^suma_control=0x[0-9a-f]+ distinta de la calculada=0x[0-9a-f]+$"):
        leer_cabecera(bytes(datos))


def test_suma_de_control_puede_omitirse() -> None:
    datos = bytearray(_contenedor_valido())
    datos[0x7FC] ^= 0xFF
    assert len(leer_cabecera(bytes(datos), verificar_suma=False).secciones) == 3


def test_calculo_de_suma_trata_los_bytes_como_enteros_con_signo() -> None:
    assert calcular_suma_control(b"\x80" * 0x7FC) == (-128 * 0x7FC) & 0xFFFFFFFF
    assert calcular_suma_control(b"\x01" * 0x7FC) == 0x7FC
    assert calcular_suma_control(b"\x01" * 0x7FC + b"\xff" * 100) == 0x7FC


def test_calculo_de_suma_rechaza_datos_cortos() -> None:
    with pytest.raises(ValueError) as error:
        calcular_suma_control(bytes(0x7FB))
    assert str(error.value) == "datos demasiado cortos: se esperaban al menos 2044 bytes"


def test_nombre_de_archivo_de_seccion_tiene_dos_digitos() -> None:
    assert nombre_archivo_seccion(2, 3) == "02_tipo03.bin"
    assert nombre_archivo_seccion(12, 10) == "12_tipo10.bin"


def test_nombre_de_archivo_de_seccion_rechaza_negativos() -> None:
    with pytest.raises(ValueError) as error:
        nombre_archivo_seccion(-1, 3)
    assert str(error.value) == "indice=-1 y tipo=3 deben ser no negativos"


@pytest.mark.parametrize("diferencia", [-3, 0, 1, 3])
def test_consumo_dentro_de_la_tolerancia_se_acepta(diferencia: int) -> None:
    validar_consumo(0, 100 + diferencia, 100)


@pytest.mark.parametrize("diferencia", [-4, 4])
def test_consumo_fuera_de_la_tolerancia_se_rechaza(diferencia: int) -> None:
    with pytest.raises(ValueError) as error:
        validar_consumo(2, 100 + diferencia, 100)
    assert str(error.value) == (
        f"secciones[2]: bytes consumidos={100 + diferencia} no concuerda con tamano=100 (diferencia maxima 3)"
    )
