"""
Reglas de negocio del reempaquetado de la imagen.

Las pruebas con la imagen real solo corren si BBLIT_DISC apunta al `.bin` del juego; sin la
variable se omiten con un motivo explicito. El resto usa una imagen sintetica.
"""

import hashlib
import os
import struct
from pathlib import Path

import pytest
from tools.disco import dominio, imagen

from tests.disco import sintetica

RUTA_REAL = os.environ.get("BBLIT_DISC")
SHA1_ORIGINAL = "6024341f559c3789b5612e941c8d0ab227ff6361"
SOLO_CON_DISCO = pytest.mark.skipif(
    not RUTA_REAL, reason="BBLIT_DISC no definida: se omite la prueba con la imagen real"
)


def sha1_de(ruta: Path) -> str:
    with ruta.open("rb") as manejador:
        return hashlib.file_digest(manejador, "sha1").hexdigest()


@SOLO_CON_DISCO
def test_edc_y_ecc_reproducen_exactamente_los_de_sectores_reales_form_1() -> None:
    assert RUTA_REAL is not None
    with imagen.ImagenCd(Path(RUTA_REAL)) as real:
        exe = imagen.buscar_archivo(real, "SLUS_008.38")
        candidatos = [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]
        candidatos += [exe.lba, exe.lba + 1, exe.lba + 85, exe.lba + 170]
        candidatos += list(range(1000, 100000, 7919))
        validados = 0
        for lba in candidatos:
            sector = real.leer_sector(lba)
            if dominio.es_form_2(sector[16:24]):
                continue
            assert struct.unpack_from("<I", sector, 2072)[0] == dominio.calcular_edc(sector[16:2072]), lba
            assert dominio.calcular_ecc(sector) == sector[2076:], lba
            validados += 1
        assert validados >= 20


@SOLO_CON_DISCO
def test_el_directorio_real_ubica_slus_008_38_con_171_sectores() -> None:
    assert RUTA_REAL is not None
    with imagen.ImagenCd(Path(RUTA_REAL)) as real:
        exe = imagen.buscar_archivo(real, "SLUS_008.38")
    assert exe.tamano == 350208
    assert -(-exe.tamano // 2048) == 171


@SOLO_CON_DISCO
def test_reempaquetar_con_el_ejecutable_original_reproduce_la_imagen_byte_a_byte(tmp_path: Path) -> None:
    assert RUTA_REAL is not None
    ruta = Path(RUTA_REAL)
    exe_local = tmp_path / "SLUS_008.38"
    with imagen.ImagenCd(ruta) as real:
        entrada = imagen.buscar_archivo(real, "SLUS_008.38")
        contenido = b"".join(dominio.extraer_datos(real.leer_sector(entrada.lba + i)) for i in range(171))
    exe_local.write_bytes(contenido[: entrada.tamano])
    resultado = imagen.reempaquetar(ruta, exe_local, tmp_path / "salida")
    assert resultado.sectores_modificados == 0
    assert resultado.sha1 == SHA1_ORIGINAL
    assert sha1_de(resultado.ruta_bin) == SHA1_ORIGINAL


@SOLO_CON_DISCO
def test_un_byte_cambiado_en_el_ejecutable_real_toca_un_solo_sector_con_edc_ecc_validos(
    tmp_path: Path,
) -> None:
    assert RUTA_REAL is not None
    ruta = Path(RUTA_REAL)
    with imagen.ImagenCd(ruta) as real:
        entrada = imagen.buscar_archivo(real, "SLUS_008.38")
        contenido = bytearray(
            b"".join(dominio.extraer_datos(real.leer_sector(entrada.lba + i)) for i in range(171))
        )
    contenido[0x800 + 5] ^= 0xFF
    exe = tmp_path / "SLUS_008.38"
    exe.write_bytes(bytes(contenido))
    resultado = imagen.reempaquetar(ruta, exe, tmp_path / "salida")
    assert resultado.sectores_modificados == 1
    with imagen.ImagenCd(resultado.ruta_bin) as nueva:
        sector = nueva.leer_sector(entrada.lba + 1)
    assert dominio.extraer_datos(sector)[5] == contenido[0x800 + 5]
    assert struct.unpack_from("<I", sector, 2072)[0] == dominio.calcular_edc(sector[16:2072])
    assert dominio.calcular_ecc(sector) == sector[2076:]


def test_la_sustitucion_con_ejecutable_distinto_de_tamano_exige_reconstruir_la_imagen(tmp_path: Path) -> None:
    ruta = tmp_path / "juego.bin"
    sintetica.construir_imagen(ruta)
    exe = tmp_path / "SLUS_008.38"
    exe.write_bytes(sintetica.contenido_exe() + b"\x00")
    with pytest.raises(ValueError, match="hace falta reconstruir la imagen completa"):
        imagen.reempaquetar(ruta, exe, tmp_path / "salida")


def test_la_imagen_de_entrada_queda_intacta_tras_reempaquetar(tmp_path: Path) -> None:
    ruta = tmp_path / "juego.bin"
    sintetica.construir_imagen(ruta)
    antes = sha1_de(ruta)
    exe = tmp_path / "SLUS_008.38"
    exe.write_bytes(bytes(sintetica.TAMANO_EXE))
    resultado = imagen.reempaquetar(ruta, exe, tmp_path / "salida")
    assert sha1_de(ruta) == antes
    assert resultado.sectores_modificados == 2
    assert sha1_de(resultado.ruta_bin) != antes


def test_el_ultimo_sector_parcial_se_rellena_con_ceros(tmp_path: Path) -> None:
    ruta = tmp_path / "juego.bin"
    sintetica.construir_imagen(ruta)
    exe = tmp_path / "SLUS_008.38"
    exe.write_bytes(b"\xaa" * sintetica.TAMANO_EXE)
    resultado = imagen.reempaquetar(ruta, exe, tmp_path / "salida")
    with imagen.ImagenCd(resultado.ruta_bin) as nueva:
        ultimo = dominio.extraer_datos(nueva.leer_sector(sintetica.LBA_EXE + 1))
    restante = sintetica.TAMANO_EXE - 2048
    assert ultimo == b"\xaa" * restante + b"\x00" * (2048 - restante)


def test_los_sectores_form_2_de_audio_nunca_se_reescriben(tmp_path: Path) -> None:
    ruta = tmp_path / "juego.bin"
    sintetica.construir_imagen(ruta)
    original = ruta.read_bytes()
    exe = tmp_path / "SLUS_008.38"
    exe.write_bytes(bytes(sintetica.TAMANO_EXE))
    resultado = imagen.reempaquetar(ruta, exe, tmp_path / "salida")
    inicio = sintetica.LBA_AUDIO * 2352
    assert resultado.ruta_bin.read_bytes()[inicio : inicio + 2352] == original[inicio : inicio + 2352]


def test_el_cue_generado_referencia_el_bin_nuevo_por_nombre_relativo(tmp_path: Path) -> None:
    ruta = tmp_path / "con espacios (1).bin"
    sintetica.construir_imagen(ruta)
    exe = tmp_path / "SLUS_008.38"
    exe.write_bytes(sintetica.contenido_exe())
    resultado = imagen.reempaquetar(ruta, exe, tmp_path / "salida")
    assert resultado.ruta_cue.read_text(encoding="ascii").splitlines()[0] == 'FILE "bblit_prueba.bin" BINARY'
