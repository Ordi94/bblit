"""Pruebas del descompresor con vectores escritos a mano a partir de la especificacion."""

import pytest
from tools.bzz.descompresion import (
    ResultadoDescompresion,
    construir_tabla_longitudes,
    descomprimir,
    descomprimir_detallado,
)


def test_literal_puro_reproduce_los_bytes() -> None:
    # parametros 0x0B, n=3 (cuatro operaciones), banderas 0xFF (todo literales)
    flujo = bytes([0x0B, 0x00, 0x00, 0x03, 0xFF, 0x41, 0x42, 0x43, 0x44])
    assert descomprimir(flujo) == b"ABCD"


def test_referencia_hacia_atras_copia_desde_la_distancia_indicada() -> None:
    # dos literales y una referencia: codigo 0x0022 = distancia 2, indice 2 (longitud 5)
    flujo = bytes([0x0B, 0x00, 0x00, 0x02, 0x03, 0x61, 0x62, 0x00, 0x22])
    assert descomprimir(flujo) == b"abababa"


def test_referencia_que_se_solapa_consigo_misma_replica_el_patron() -> None:
    # un literal y una referencia de distancia 1 y longitud 3: codigo 0x0010
    flujo = bytes([0x0B, 0x00, 0x00, 0x01, 0x01, 0x78, 0x00, 0x10])
    assert descomprimir(flujo) == b"xxxx"


def test_referencia_larga_usa_la_escala_de_longitudes() -> None:
    # indice 8 con escala 1: longitud 12 (distancia 1)
    flujo = bytes([0x0B, 0x00, 0x00, 0x01, 0x01, 0x7A, 0x00, 0x18])
    assert descomprimir(flujo) == b"z" * 13
    # indice 15: longitud 26
    flujo = bytes([0x0B, 0x00, 0x00, 0x01, 0x01, 0x7A, 0x00, 0x1F])
    assert descomprimir(flujo) == b"z" * 27


def test_la_distancia_usa_los_doce_bits_altos_del_codigo() -> None:
    contenido = bytes(range(1, 101))
    # 101 operaciones: doce grupos de ocho literales, cuatro literales y una referencia
    # de distancia 100 y longitud 3 (codigo (100 << 4) | 0 = 0x0640)
    flujo = bytearray([0x0B, 0x00, 0x00, 100])
    for grupo in range(12):
        flujo += bytes([0xFF]) + contenido[grupo * 8 : grupo * 8 + 8]
    flujo += bytes([0x0F]) + contenido[96:100] + bytes([0x06, 0x40])
    assert descomprimir(bytes(flujo)) == contenido + contenido[:3]


def test_el_flujo_recarga_banderas_cada_ocho_operaciones() -> None:
    flujo = bytes([0x0B, 0x00, 0x00, 0x08, 0xFF, 1, 2, 3, 4, 5, 6, 7, 8, 0x01, 9])
    assert descomprimir(flujo) == bytes(range(1, 10))


def test_parametros_con_k_siete_usan_una_sola_longitud() -> None:
    # 0x0F: k=7 y escala 1; el codigo completo es la distancia y la longitud siempre es 3
    flujo = bytes([0x0F, 0x00, 0x00, 0x01, 0x01, 0x61, 0x00, 0x01])
    assert descomprimir(flujo) == b"aaaa"


def test_detallado_informa_consumo_y_acepta_relleno_posterior() -> None:
    flujo = bytes([0x0B, 0x00, 0x00, 0x03, 0xFF, 0x41, 0x42, 0x43, 0x44])
    resultado = descomprimir_detallado(flujo + bytes(100))
    assert resultado == ResultadoDescompresion(datos=b"ABCD", bytes_consumidos=9, relleno_final=0)


def test_referencia_final_de_distancia_cero_se_omite_y_se_informa() -> None:
    flujo = bytes([0x0B, 0x00, 0x00, 0x01, 0x01, 0x41, 0x00, 0x00])
    resultado = descomprimir_detallado(flujo)
    assert resultado.datos == b"A"
    assert resultado.relleno_final == 3
    assert resultado.bytes_consumidos == 8


def test_referencia_de_distancia_cero_antes_del_final_se_rechaza() -> None:
    flujo = bytes([0x0B, 0x00, 0x00, 0x02, 0x01, 0x41, 0x00, 0x00, 0x42])
    with pytest.raises(ValueError, match=r"^referencia con distancia=0 antes de la ultima operacion$"):
        descomprimir(flujo)


def test_referencia_anterior_al_inicio_de_la_salida_se_rechaza() -> None:
    flujo = bytes([0x0B, 0x00, 0x00, 0x00, 0x00, 0x00, 0x20])
    with pytest.raises(ValueError, match=r"^referencia con distancia=2 fuera de la salida \(0 bytes\)$"):
        descomprimir(flujo)


def test_referencia_mas_lejos_que_lo_producido_se_rechaza() -> None:
    flujo = bytes([0x0B, 0x00, 0x00, 0x01, 0x01, 0x41, 0x00, 0x20])
    with pytest.raises(ValueError, match=r"distancia=2 fuera de la salida \(1 bytes\)"):
        descomprimir(flujo)


@pytest.mark.parametrize(
    "flujo",
    [
        bytes([0x0B, 0x00, 0x00, 0x03, 0xFF, 0x41]),
        bytes([0x0B, 0x00, 0x00, 0x03]),
        bytes([0x0B, 0x00, 0x00, 0x01, 0x01, 0x41, 0x00]),
    ],
    ids=["literales_faltantes", "sin_banderas", "referencia_sin_segundo_byte"],
)
def test_flujo_truncado_se_rechaza_sin_leer_fuera_de_rango(flujo: bytes) -> None:
    with pytest.raises(ValueError, match=r"^flujo comprimido truncado"):
        descomprimir(flujo)


def test_flujo_menor_a_la_cabecera_se_rechaza() -> None:
    with pytest.raises(ValueError, match=r"^flujo demasiado corto: se esperaban al menos 4 bytes$"):
        descomprimir(b"\x0b\x00\x00")


def test_parametros_con_bits_reservados_se_rechazan() -> None:
    with pytest.raises(ValueError, match=r"^parametros=0x2b usa bits reservados \(5-7\), se esperaba 0$"):
        descomprimir(bytes([0x2B, 0x00, 0x00, 0x00, 0x01, 0x41]))


def test_parametros_con_k_menor_al_minimo_se_rechazan() -> None:
    with pytest.raises(ValueError, match=r"^parametros=0x02 tiene k=2, se esperaba 3..7$"):
        descomprimir(bytes([0x02, 0x00, 0x00, 0x00, 0x01, 0x41]))


def test_salida_que_supera_el_limite_se_rechaza_con_literales() -> None:
    flujo = bytes([0x0B, 0x00, 0x00, 0x03, 0xFF, 0x41, 0x42, 0x43, 0x44])
    with pytest.raises(ValueError, match=r"^salida supera el limite de 3 bytes$"):
        descomprimir(flujo, limite_salida=3)


def test_salida_que_supera_el_limite_se_rechaza_con_referencias() -> None:
    flujo = bytes([0x0B, 0x00, 0x00, 0x01, 0x01, 0x7A, 0x00, 0x1F])
    with pytest.raises(ValueError, match=r"^salida supera el limite de 10 bytes$"):
        descomprimir(flujo, limite_salida=10)


def test_tabla_de_longitudes_para_k_tres_y_escala_uno() -> None:
    assert construir_tabla_longitudes(3, 1) == (3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 22, 24, 26)


def test_tabla_de_longitudes_para_k_cuatro_y_escala_cero() -> None:
    assert construir_tabla_longitudes(4, 0) == (3, 4, 5, 6, 7, 8, 9, 10)


def test_tabla_de_longitudes_para_k_cuatro_y_escala_tres() -> None:
    assert construir_tabla_longitudes(4, 3) == (3, 4, 5, 6, 3 + 3 + 8, 3 + 3 + 16, 3 + 3 + 24, 3 + 3 + 32)


def test_tabla_de_longitudes_para_k_siete_tiene_una_entrada() -> None:
    assert construir_tabla_longitudes(7, 0) == (3,)


@pytest.mark.parametrize("k", [2, 8])
def test_tabla_de_longitudes_rechaza_k_fuera_de_rango(k: int) -> None:
    with pytest.raises(ValueError, match=rf"^k={k} fuera de rango 3..7$"):
        construir_tabla_longitudes(k, 0)


def test_tabla_de_longitudes_rechaza_escala_fuera_de_rango() -> None:
    with pytest.raises(ValueError, match=r"^escala=4 fuera de rango 0..3$"):
        construir_tabla_longitudes(3, 4)
