"""Constructor de imagenes MODE2/2352 sinteticas para las pruebas de `tools.disco`."""

from __future__ import annotations

import struct
from pathlib import Path

from tools.disco import dominio

SUBCABECERA_FORM1 = bytes([0, 0, 0x08, 0, 0, 0, 0x08, 0])
SUBCABECERA_FORM2 = bytes([1, 1, 0x64, 1, 1, 1, 0x64, 1])
LBA_RAIZ = 18
LBA_SUBDIR = 19
LBA_EXE = 20
SECTORES_EXE = 2
TAMANO_EXE = 3000
LBA_INTERNO = 22
LBA_AUDIO = 23
TOTAL_SECTORES = 25


def _bcd(valor: int) -> int:
    """Codifica un entero 0..99 en BCD."""
    return ((valor // 10) << 4) | (valor % 10)


def sector_crudo(lba: int, datos: bytes, subcabecera: bytes = SUBCABECERA_FORM1) -> bytes:
    """Arma un sector Mode 2 con EDC/ECC calculados (Form 1) o relleno (Form 2)."""
    total = lba + 150
    cabecera = bytes([_bcd(total // 4500), _bcd(total // 75 % 60), _bcd(total % 75), 2])
    base = dominio.SINCRONIA + cabecera + subcabecera
    if subcabecera[2] & dominio.MASCARA_FORM_2:
        return (base + datos.ljust(2324, b"\x00")).ljust(dominio.TAMANO_SECTOR_CRUDO, b"\x00")
    vacio = base + b"\x00" * (dominio.TAMANO_SECTOR_CRUDO - len(base))
    return dominio.construir_sector_form1(vacio, datos.ljust(dominio.TAMANO_DATOS, b"\x00"))


def registro(nombre: bytes, lba: int, tamano: int, directorio: bool = False) -> bytes:
    """Arma un registro de directorio ISO 9660 con relleno par."""
    largo = 33 + len(nombre)
    largo += largo % 2
    cuerpo = bytearray(largo)
    cuerpo[0] = largo
    struct.pack_into("<I", cuerpo, 2, lba)
    struct.pack_into(">I", cuerpo, 6, lba)
    struct.pack_into("<I", cuerpo, 10, tamano)
    struct.pack_into(">I", cuerpo, 14, tamano)
    cuerpo[25] = 0x02 if directorio else 0
    cuerpo[32] = len(nombre)
    cuerpo[33 : 33 + len(nombre)] = nombre
    return bytes(cuerpo)


def contenido_exe() -> bytes:
    """Contenido determinista del ejecutable sintetico."""
    return bytes((i * 7 + 3) % 256 for i in range(TAMANO_EXE))


def construir_imagen(ruta: Path) -> None:
    """Escribe una imagen de 25 sectores con raiz, subdirectorio, ejecutable y un archivo Form 2."""
    sectores = {lba: sector_crudo(lba, b"") for lba in range(TOTAL_SECTORES)}
    descriptor = bytearray(dominio.TAMANO_DATOS)
    descriptor[0:6] = b"\x01CD001"
    descriptor[156 : 156 + 34] = registro(b"\x00", LBA_RAIZ, 2048, directorio=True)[:34]
    descriptor[156] = 34
    sectores[16] = sector_crudo(16, bytes(descriptor))
    raiz = (
        registro(b"\x00", LBA_RAIZ, 2048, True)
        + registro(b"\x01", LBA_RAIZ, 2048, True)
        + registro(b"SLUS_008.38;1", LBA_EXE, TAMANO_EXE)
        + registro(b"DIR", LBA_SUBDIR, 2048, True)
        + registro(b"AUDIO.XA;1", LBA_AUDIO, 2324)
    )
    sectores[LBA_RAIZ] = sector_crudo(LBA_RAIZ, raiz)
    sectores[LBA_SUBDIR] = sector_crudo(LBA_SUBDIR, registro(b"INNER.BIN;1", LBA_INTERNO, 2048))
    contenido = contenido_exe()
    sectores[LBA_EXE] = sector_crudo(LBA_EXE, contenido[:2048])
    sectores[LBA_EXE + 1] = sector_crudo(LBA_EXE + 1, contenido[2048:])
    sectores[LBA_INTERNO] = sector_crudo(LBA_INTERNO, b"interno")
    sectores[LBA_AUDIO] = sector_crudo(LBA_AUDIO, b"audio", SUBCABECERA_FORM2)
    ruta.write_bytes(b"".join(sectores[lba] for lba in range(TOTAL_SECTORES)))
