"""Constructores de datos sinteticos para las pruebas del paquete bzz.

Todo se arma a mano a partir de la especificacion del formato (``docs/FORMATO_BZZ.md``):
ningun dato procede del disco original.
"""

from __future__ import annotations

import struct

TAMANO_SECTOR = 0x800
LONGITUDES_PERMITIDAS = (*range(3, 11), *range(12, 27, 2))


def flujo_literales(contenido: bytes, parametros: int = 0x0B) -> bytes:
    """Codifica ``contenido`` como un flujo de solo literales."""
    n = len(contenido) - 1
    cabecera = bytes([parametros, (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF])
    cuerpo = bytearray()
    for inicio in range(0, len(contenido), 8):
        cuerpo.append(0xFF)
        cuerpo += contenido[inicio : inicio + 8]
    return cabecera + bytes(cuerpo)


def comprimir(contenido: bytes) -> bytes:
    """Compresor ingenuo (k=3, escala 1) que usa referencias cuando ahorran espacio.

    Busca la coincidencia mas larga dentro de la ventana de 4095 bytes y solo emite una
    referencia si la longitud es 3 o mayor. Sirve para comprobar el descompresor con
    flujos que contienen referencias de distintas distancias y longitudes.
    """
    operaciones: list[tuple[int, int] | int] = []
    posicion = 0
    while posicion < len(contenido):
        mejor_longitud = 0
        mejor_distancia = 0
        for distancia in range(1, min(posicion, 4095) + 1):
            longitud = 0
            while (
                longitud < 26
                and posicion + longitud < len(contenido)
                and contenido[posicion + longitud - distancia] == contenido[posicion + longitud]
            ):
                longitud += 1
            while longitud >= 3 and longitud not in LONGITUDES_PERMITIDAS:
                longitud -= 1
            if longitud > mejor_longitud:
                mejor_longitud, mejor_distancia = longitud, distancia
        if mejor_longitud >= 3:
            operaciones.append((mejor_distancia, mejor_longitud))
            posicion += mejor_longitud
        else:
            operaciones.append(contenido[posicion])
            posicion += 1
    n = len(operaciones) - 1
    flujo = bytearray([0x0B, (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF])
    for inicio in range(0, len(operaciones), 8):
        grupo = operaciones[inicio : inicio + 8]
        banderas = 0
        cuerpo = bytearray()
        for bit, operacion in enumerate(grupo):
            if isinstance(operacion, int):
                banderas |= 1 << bit
                cuerpo.append(operacion)
            else:
                distancia, longitud = operacion
                indice = longitud - 3 if longitud <= 10 else 7 + (longitud - 3 - 7) // 2
                cuerpo += struct.pack(">H", (distancia << 4) | indice)
        flujo.append(banderas)
        flujo += cuerpo
    return bytes(flujo)


def suma_control(primer_sector: bytes) -> int:
    """Suma de los primeros 0x7FC bytes como enteros con signo, a 32 bits."""
    total = sum(valor - 256 if valor >= 0x80 else valor for valor in primer_sector[:0x7FC])
    return total & 0xFFFFFFFF


def alinear(tamano: int) -> int:
    """Redondea hacia arriba a un multiplo de ``TAMANO_SECTOR``."""
    return (tamano + TAMANO_SECTOR - 1) // TAMANO_SECTOR * TAMANO_SECTOR


def construir_bzz(secciones: list[tuple[int, bytes]], version: int = 1) -> bytes:
    """Arma un contenedor con la lista de ``(tipo, flujo_comprimido)`` dada."""
    cabecera = bytearray(TAMANO_SECTOR)
    struct.pack_into("<II", cabecera, 0, version, len(secciones))
    cuerpo = bytearray()
    for indice, (tipo, flujo) in enumerate(secciones):
        alineado = alinear(len(flujo))
        struct.pack_into("<III", cabecera, 8 + 12 * indice, tipo, len(flujo), alineado)
        cuerpo += flujo + bytes(alineado - len(flujo))
    struct.pack_into("<I", cabecera, 0x7FC, suma_control(bytes(cabecera)))
    return bytes(cabecera) + bytes(cuerpo)
