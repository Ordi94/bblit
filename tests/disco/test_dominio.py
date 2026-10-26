import struct

import pytest
from tools.disco import dominio

from tests.disco import sintetica


def crc_bit_a_bit(datos: bytes) -> int:
    """Implementacion independiente del CRC del EDC, bit a bit."""
    edc = 0
    for byte in datos:
        edc ^= byte
        for _ in range(8):
            edc = (edc >> 1) ^ (0xD8018001 if edc & 1 else 0)
    return edc


def test_lba_a_offset_multiplica_por_el_sector_crudo() -> None:
    assert dominio.lba_a_offset(0) == 0
    assert dominio.lba_a_offset(16) == 37632
    assert dominio.lba_a_offset(249594) == 249594 * 2352


def test_lba_a_offset_rechaza_negativos() -> None:
    with pytest.raises(ValueError, match="lba=-1 fuera de rango: se esperaba un valor >= 0"):
        dominio.lba_a_offset(-1)


def test_es_form_2_distingue_por_el_bit_5_del_submodo() -> None:
    assert dominio.es_form_2(sintetica.SUBCABECERA_FORM2) is True
    assert dominio.es_form_2(sintetica.SUBCABECERA_FORM1) is False


def test_es_form_2_exige_ocho_bytes() -> None:
    with pytest.raises(ValueError, match="subcabecera de 3 bytes: se esperaban 8"):
        dominio.es_form_2(b"abc")


def test_validar_sector_crudo_acepta_un_sector_correcto() -> None:
    dominio.validar_sector_crudo(sintetica.sector_crudo(0, b"x"))


def test_validar_sector_crudo_rechaza_tamano_sincronia_y_modo() -> None:
    sector = sintetica.sector_crudo(0, b"x")
    with pytest.raises(ValueError, match="sector de 10 bytes: se esperaban 2352"):
        dominio.validar_sector_crudo(sector[:10])
    with pytest.raises(ValueError, match="sincronia del sector invalida"):
        dominio.validar_sector_crudo(b"\x01" + sector[1:])
    modo1 = sector[:15] + b"\x01" + sector[16:]
    with pytest.raises(ValueError, match="modo=1 no soportado: se esperaba 2"):
        dominio.validar_sector_crudo(modo1)


def test_edc_de_ceros_es_cero_y_coincide_con_la_implementacion_bit_a_bit() -> None:
    assert dominio.calcular_edc(b"\x00" * 2056) == 0
    muestra = bytes(range(256)) * 8 + b"\xff" * 8
    assert dominio.calcular_edc(muestra) == crc_bit_a_bit(muestra)


def test_ecc_de_un_sector_de_ceros_es_cero() -> None:
    sector = dominio.SINCRONIA + b"\x00\x02\x00\x02" + b"\x00" * (2352 - 16)
    assert dominio.calcular_ecc(sector) == b"\x00" * dominio.TAMANO_ECC


def test_ecc_ignora_la_direccion_de_la_cabecera() -> None:
    a = sintetica.sector_crudo(5, b"mismo contenido")
    b = sintetica.sector_crudo(900, b"mismo contenido")
    assert a[12:16] != b[12:16]
    assert dominio.calcular_ecc(a) == dominio.calcular_ecc(b)


def test_ecc_mide_172_mas_104_bytes_y_exige_sector_completo() -> None:
    sector = sintetica.sector_crudo(0, b"abc")
    assert len(dominio.calcular_ecc(sector)) == 276
    with pytest.raises(ValueError, match="sector de 5 bytes: se esperaban 2352"):
        dominio.calcular_ecc(b"12345")


def test_construir_sector_form1_conserva_cabeceras_y_actualiza_edc_ecc() -> None:
    original = sintetica.sector_crudo(7, b"viejo")
    nuevo = dominio.construir_sector_form1(original, b"nuevo".ljust(2048, b"\x00"))
    assert nuevo[:24] == original[:24]
    assert nuevo[24:2072] == b"nuevo".ljust(2048, b"\x00")
    assert struct.unpack_from("<I", nuevo, 2072)[0] == crc_bit_a_bit(nuevo[16:2072])
    assert nuevo[2076:] == dominio.calcular_ecc(nuevo)
    assert nuevo != original


def test_construir_sector_form1_rechaza_form_2_y_datos_de_otro_tamano() -> None:
    form2 = sintetica.sector_crudo(3, b"a", sintetica.SUBCABECERA_FORM2)
    with pytest.raises(ValueError, match="el sector es Form 2"):
        dominio.construir_sector_form1(form2, b"\x00" * 2048)
    form1 = sintetica.sector_crudo(3, b"a")
    with pytest.raises(ValueError, match="datos de 10 bytes: se esperaban 2048"):
        dominio.construir_sector_form1(form1, b"0123456789")


def test_extraer_datos_devuelve_2048_bytes_y_rechaza_form_2() -> None:
    sector = sintetica.sector_crudo(3, b"hola")
    assert dominio.extraer_datos(sector) == b"hola".ljust(2048, b"\x00")
    with pytest.raises(ValueError, match="solo los sectores Form 1"):
        dominio.extraer_datos(sintetica.sector_crudo(3, b"a", sintetica.SUBCABECERA_FORM2))


def test_parsear_directorio_lee_lba_tamano_y_marca_de_directorio() -> None:
    datos = (
        sintetica.registro(b"SLUS_008.38;1", 20, 350208)
        + sintetica.registro(b"DIR", 30, 2048, True)
        + b"\x00" * 100
    )
    archivo, carpeta = dominio.parsear_directorio(datos)
    assert archivo == dominio.EntradaDirectorio("SLUS_008.38;1", 20, 350208, False)
    assert carpeta == dominio.EntradaDirectorio("DIR", 30, 2048, True)


def test_parsear_directorio_detiene_en_el_relleno_de_ceros() -> None:
    datos = sintetica.registro(b"A;1", 1, 1) + b"\x00" + sintetica.registro(b"B;1", 2, 2)
    assert [e.nombre for e in dominio.parsear_directorio(datos)] == ["A;1"]


def test_parsear_directorio_rechaza_registros_invalidos() -> None:
    with pytest.raises(ValueError, match="longitud de registro=10 fuera de rango en el offset 0"):
        dominio.parsear_directorio(bytes([10]) + b"\x00" * 40)
    with pytest.raises(ValueError, match="longitud de registro=60 fuera de rango"):
        dominio.parsear_directorio(bytes([60]) + b"\x00" * 40)
    desborda = bytearray(sintetica.registro(b"AB", 1, 1))
    desborda[32] = 200
    with pytest.raises(ValueError, match="largo de nombre=200 desborda el registro de 36 bytes"):
        dominio.parsear_directorio(bytes(desborda))
    demasiados = sintetica.registro(b"A", 1, 1) * 129
    with pytest.raises(ValueError, match="mas de 128 registros"):
        dominio.parsear_directorio(demasiados)


def test_parsear_raiz_lee_el_registro_del_descriptor() -> None:
    descriptor = bytearray(2048)
    descriptor[0:6] = b"\x01CD001"
    descriptor[156 : 156 + 34] = sintetica.registro(b"\x00", 18, 2048, True)[:34]
    raiz = dominio.parsear_raiz(bytes(descriptor))
    assert (raiz.lba, raiz.tamano, raiz.es_directorio) == (18, 2048, True)


def test_parsear_raiz_rechaza_descriptores_invalidos() -> None:
    with pytest.raises(ValueError, match="descriptor de 5 bytes: se esperaban 2048"):
        dominio.parsear_raiz(b"12345")
    with pytest.raises(ValueError, match="no es un descriptor primario"):
        dominio.parsear_raiz(b"\x00" * 2048)
    sin_raiz = bytearray(2048)
    sin_raiz[0:6] = b"\x01CD001"
    with pytest.raises(ValueError, match="registro del directorio raiz invalido"):
        dominio.parsear_raiz(bytes(sin_raiz))


def test_normalizar_nombre_quita_version_y_pasa_a_mayusculas() -> None:
    assert dominio.normalizar_nombre("slus_008.38;1") == "SLUS_008.38"
    assert dominio.normalizar_nombre("MUSIC.XA") == "MUSIC.XA"


def test_validar_tamano_ejecutable_acepta_igual_y_rechaza_distinto_con_mensaje_exacto() -> None:
    dominio.validar_tamano_ejecutable(350208, 350208)
    mensaje = (
        "tamano del ejecutable=350209 distinto del registrado en la imagen (350208): "
        "hace falta reconstruir la imagen completa"
    )
    with pytest.raises(ValueError) as info:
        dominio.validar_tamano_ejecutable(350209, 350208)
    assert str(info.value) == mensaje


def test_generar_cue_referencia_el_bin_por_nombre_relativo() -> None:
    assert dominio.generar_cue("bblit_prueba.bin") == (
        'FILE "bblit_prueba.bin" BINARY\r\n  TRACK 01 MODE2/2352\r\n    INDEX 01 00:00:00\r\n'
    )


@pytest.mark.parametrize("nombre", ["", "a/b.bin", "a\\b.bin", 'a"b.bin'])
def test_generar_cue_rechaza_nombres_con_ruta_o_comillas(nombre: str) -> None:
    with pytest.raises(ValueError, match="nombre_bin debe ser un nombre de archivo"):
        dominio.generar_cue(nombre)
