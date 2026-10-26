from pathlib import Path

import pytest
from tools.disco import dominio, imagen

from tests.disco import sintetica


@pytest.fixture
def ruta_imagen(tmp_path: Path) -> Path:
    ruta = tmp_path / "origen" / "juego (v1).bin"
    ruta.parent.mkdir()
    sintetica.construir_imagen(ruta)
    return ruta


def test_imagen_rechaza_tamanos_que_no_son_multiplo_del_sector(tmp_path: Path) -> None:
    ruta = tmp_path / "mala.bin"
    ruta.write_bytes(b"\x00" * 2353)
    with pytest.raises(ValueError, match="tamano de imagen=2353: se esperaba un multiplo de 2352"):
        imagen.ImagenCd(ruta)
    ruta.write_bytes(b"")
    with pytest.raises(ValueError, match="tamano de imagen=0"):
        imagen.ImagenCd(ruta)


def test_leer_y_escribir_sector_respetan_las_cotas(ruta_imagen: Path) -> None:
    with imagen.ImagenCd(ruta_imagen, escritura=True) as lectura:
        assert lectura.total_sectores == sintetica.TOTAL_SECTORES
        sector = lectura.leer_sector(16)
        assert sector[:12] == dominio.SINCRONIA
        with pytest.raises(ValueError, match=r"lba=25 fuera de rango 0..24"):
            lectura.leer_sector(25)
        with pytest.raises(ValueError, match=r"lba=-1 fuera de rango 0..24"):
            lectura.leer_sector(-1)
        with pytest.raises(ValueError, match="sector de 3 bytes: se esperaban 2352"):
            lectura.escribir_sector(1, b"abc")
        lectura.escribir_sector(1, sector)
    with imagen.ImagenCd(ruta_imagen) as lectura:
        assert lectura.leer_sector(1) == sector


def test_buscar_archivo_lee_lba_y_tamano_del_directorio(ruta_imagen: Path) -> None:
    with imagen.ImagenCd(ruta_imagen) as lectura:
        exe = imagen.buscar_archivo(lectura, "slus_008.38")
        interno = imagen.buscar_archivo(lectura, "DIR/INNER.BIN")
    assert (exe.lba, exe.tamano) == (sintetica.LBA_EXE, sintetica.TAMANO_EXE)
    assert (interno.lba, interno.tamano) == (sintetica.LBA_INTERNO, 2048)


@pytest.mark.parametrize(
    ("ruta", "mensaje"),
    [
        ("", "ruta con 0 componentes: se esperaban 1..8"),
        ("a/b/c/d/e/f/g/h/i", "ruta con 9 componentes: se esperaban 1..8"),
        ("NO_EXISTE.BIN", "componente 'NO_EXISTE.BIN' no encontrado"),
        ("SLUS_008.38/X", "componente 'SLUS_008.38' no es un directorio"),
        ("DIR", "'DIR' es un directorio, se esperaba un archivo"),
    ],
)
def test_buscar_archivo_rechaza_rutas_invalidas(ruta_imagen: Path, ruta: str, mensaje: str) -> None:
    with imagen.ImagenCd(ruta_imagen) as lectura, pytest.raises(ValueError, match=mensaje):
        imagen.buscar_archivo(lectura, ruta)


def test_buscar_archivo_rechaza_archivos_fuera_de_la_imagen(tmp_path: Path) -> None:
    ruta = tmp_path / "corta.bin"
    sintetica.construir_imagen(ruta)
    datos = ruta.read_bytes()
    ruta.write_bytes(datos[: 21 * dominio.TAMANO_SECTOR_CRUDO])
    with imagen.ImagenCd(ruta) as lectura, pytest.raises(ValueError, match="fuera de la imagen"):
        imagen.buscar_archivo(lectura, "SLUS_008.38")


def test_buscar_archivo_rechaza_directorios_desproporcionados(
    ruta_imagen: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(imagen, "MAX_SECTORES_DIRECTORIO", 0)
    with imagen.ImagenCd(ruta_imagen) as lectura, pytest.raises(ValueError, match="directorio de 1 sectores"):
        imagen.buscar_archivo(lectura, "SLUS_008.38")


def test_reempaquetar_con_el_mismo_contenido_no_modifica_ningun_sector(
    ruta_imagen: Path, tmp_path: Path
) -> None:
    exe = tmp_path / "SLUS_008.38"
    exe.write_bytes(sintetica.contenido_exe())
    resultado = imagen.reempaquetar(ruta_imagen, exe, tmp_path / "salida (1)")
    assert resultado.sectores_modificados == 0
    assert resultado.sectores_totales == sintetica.TOTAL_SECTORES
    assert resultado.ruta_bin.read_bytes() == ruta_imagen.read_bytes()
    assert (
        resultado.ruta_cue.read_bytes()
        == b'FILE "bblit_prueba.bin" BINARY\r\n  TRACK 01 MODE2/2352\r\n    INDEX 01 00:00:00\r\n'
    )
    assert not (tmp_path / "salida (1)" / "bblit_prueba.bin.parcial").exists()


def test_reempaquetar_sustituye_solo_los_sectores_del_ejecutable(ruta_imagen: Path, tmp_path: Path) -> None:
    original = ruta_imagen.read_bytes()
    nuevo = bytearray(sintetica.contenido_exe())
    nuevo[2100] ^= 0xFF
    exe = tmp_path / "nuevo.exe"
    exe.write_bytes(bytes(nuevo))
    resultado = imagen.reempaquetar(ruta_imagen, exe, tmp_path / "salida")
    assert resultado.sectores_modificados == 1
    producido = resultado.ruta_bin.read_bytes()
    assert ruta_imagen.read_bytes() == original
    cambiados = [
        lba
        for lba in range(sintetica.TOTAL_SECTORES)
        if producido[lba * 2352 : (lba + 1) * 2352] != original[lba * 2352 : (lba + 1) * 2352]
    ]
    assert cambiados == [sintetica.LBA_EXE + 1]
    sector = producido[(sintetica.LBA_EXE + 1) * 2352 : (sintetica.LBA_EXE + 2) * 2352]
    assert dominio.extraer_datos(sector)[: 3000 - 2048] == bytes(nuevo[2048:])
    assert dominio.construir_sector_form1(sector, dominio.extraer_datos(sector)) == sector


def test_reempaquetar_rechaza_un_ejecutable_de_otro_tamano(ruta_imagen: Path, tmp_path: Path) -> None:
    exe = tmp_path / "grande.exe"
    exe.write_bytes(b"\x00" * (sintetica.TAMANO_EXE + 1))
    with pytest.raises(ValueError) as info:
        imagen.reempaquetar(ruta_imagen, exe, tmp_path / "salida")
    assert str(info.value) == (
        "tamano del ejecutable=3001 distinto del registrado en la imagen (3000): "
        "hace falta reconstruir la imagen completa"
    )
    assert not (tmp_path / "salida" / "bblit_prueba.bin").exists()


def test_reempaquetar_no_pisa_la_imagen_de_entrada(tmp_path: Path) -> None:
    carpeta = tmp_path / "mismo"
    carpeta.mkdir()
    ruta = carpeta / "bblit_prueba.bin"
    sintetica.construir_imagen(ruta)
    exe = tmp_path / "x.exe"
    exe.write_bytes(sintetica.contenido_exe())
    with pytest.raises(ValueError, match="la imagen de salida coincide con la de entrada"):
        imagen.reempaquetar(ruta, exe, carpeta)


def test_reempaquetar_aborta_si_edc_ecc_no_reproducen_el_original(ruta_imagen: Path, tmp_path: Path) -> None:
    datos = bytearray(ruta_imagen.read_bytes())
    datos[sintetica.LBA_EXE * 2352 + 2100] ^= 0x55
    ruta_imagen.write_bytes(bytes(datos))
    exe = tmp_path / "x.exe"
    exe.write_bytes(sintetica.contenido_exe())
    with pytest.raises(ValueError, match="no coinciden con los del sector lba=20"):
        imagen.reempaquetar(ruta_imagen, exe, tmp_path / "salida")
    assert not (tmp_path / "salida" / "bblit_prueba.bin").exists()
    assert not (tmp_path / "salida" / "bblit_prueba.bin.parcial").exists()


def test_reempaquetar_rechaza_sustituir_un_archivo_form_2(ruta_imagen: Path, tmp_path: Path) -> None:
    exe = tmp_path / "audio.xa"
    exe.write_bytes(b"\x00" * 2324)
    with pytest.raises(ValueError, match="solo los sectores Form 1"):
        imagen.reempaquetar(ruta_imagen, exe, tmp_path / "salida", archivo="AUDIO.XA")
