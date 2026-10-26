"""Constructores de PNG y de ejecutables sinteticos para las pruebas del emulador."""

import struct
import zlib


def _chunk(tipo: bytes, contenido: bytes) -> bytes:
    return (
        struct.pack(">I", len(contenido)) + tipo + contenido + struct.pack(">I", zlib.crc32(tipo + contenido))
    )


def _filtrar(filtro: int, actual: bytes, anterior: bytes, bpp: int) -> bytes:
    """Aplica el filtro PNG `filtro` a una fila (inverso de la decodificacion)."""
    salida = bytearray()
    for i, valor in enumerate(actual):
        a = actual[i - bpp] if i >= bpp else 0
        b = anterior[i]
        c = anterior[i - bpp] if i >= bpp else 0
        if filtro == 0:
            pred = 0
        elif filtro == 1:
            pred = a
        elif filtro == 2:
            pred = b
        elif filtro == 3:
            pred = (a + b) >> 1
        else:
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            pred = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
        salida.append((valor - pred) & 0xFF)
    return bytes([filtro]) + bytes(salida)


def construir_png(
    ancho: int,
    alto: int,
    pixeles: bytes,
    tipo: int = 6,
    filtros: tuple[int, ...] = (0,),
    paleta: bytes | None = None,
    profundidad: int = 8,
    entrelazado: int = 0,
) -> bytes:
    """Construye un PNG; `filtros` se reparte por filas de forma ciclica."""
    canales = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[tipo]
    fila = ancho * canales
    anterior = bytes(fila)
    crudo = b""
    for y in range(alto):
        actual = pixeles[y * fila : (y + 1) * fila]
        crudo += _filtrar(filtros[y % len(filtros)], actual, anterior, canales)
        anterior = actual
    cabecera = struct.pack(">IIBBBBB", ancho, alto, profundidad, tipo, 0, 0, entrelazado)
    partes = [b"\x89PNG\r\n\x1a\n", _chunk(b"IHDR", cabecera)]
    if paleta is not None:
        partes.append(_chunk(b"PLTE", paleta))
    partes += [_chunk(b"IDAT", zlib.compress(crudo)), _chunk(b"IEND", b"")]
    return b"".join(partes)


def png_negro(ancho: int = 64, alto: int = 48) -> bytes:
    """PNG RGBA completamente negro (alfa opaco)."""
    return construir_png(ancho, alto, bytes([0, 0, 0, 255]) * (ancho * alto))


def png_con_contenido(ancho: int = 64, alto: int = 48, brillo: int = 200, cuantos: int = 600) -> bytes:
    """PNG RGBA negro con `cuantos` pixeles de brillo `brillo` al inicio."""
    pixeles = bytes([brillo, brillo, brillo, 255]) * cuantos + bytes([0, 0, 0, 255]) * (
        ancho * alto - cuantos
    )
    return construir_png(ancho, alto, pixeles)


def ejecutable_psx(direccion: int = 0x80014A00, texto: bytes | None = None) -> bytes:
    """PS-X EXE minimo: cabecera de 0x800 bytes con la direccion de carga y un texto de 512 bytes."""
    texto = texto if texto is not None else bytes(range(256)) * 2
    cabecera = bytearray(0x800)
    cabecera[0:8] = b"PS-X EXE"
    cabecera[0x18:0x1C] = direccion.to_bytes(4, "little")
    cabecera[0x1C:0x20] = len(texto).to_bytes(4, "little")
    return bytes(cabecera) + texto
