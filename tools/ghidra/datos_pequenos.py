"""Datos pequenos que el codigo direcciona con desplazamiento relativo a ``$gp``.

El arranque del programa fija ``$gp`` y el compilador accede a las variables pequenas con un
desplazamiento de 16 bits sobre ese registro (``lw v0, 0x18($gp)``). Ninguna firma ni analisis
de funciones los declara, pero el codigo los delata: cada desplazamiento distinto es una
variable, y el mnemonico del acceso (``lb``/``lh``/``lw``) da su ancho. Este modulo los
descubre leyendo las instrucciones del segmento, sin tablas manuales.
"""

import struct
from typing import Final, cast

from tools.ghidra.dominio import Simbolo, TipoSimbolo

REGISTRO_GP: Final[int] = 28
COTA_DIRECCION_TOMADA: Final[int] = 0x40
"""Tamano maximo que se atribuye a un dato del que solo se toma la direccion (el real se desconoce)."""
_ANCHO_POR_OPERACION: Final[dict[int, int]] = {
    0x20: 1,  # lb
    0x24: 1,  # lbu
    0x28: 1,  # sb
    0x21: 2,  # lh
    0x25: 2,  # lhu
    0x29: 2,  # sh
    0x22: 4,  # lwl
    0x23: 4,  # lw
    0x26: 4,  # lwr
    0x2A: 4,  # swl
    0x2B: 4,  # sw
    0x2E: 4,  # swr
    0x32: 4,  # lwc2
    0x3A: 4,  # swc2
}
_ADDIU: Final[int] = 9
_LUI: Final[int] = 0x0F


def leer_gp(segmento: bytes, base: int, codigo: tuple[int, int]) -> int | None:
    """
    Lee el valor que el arranque deja en ``$gp``.

    Contexto:
        El codigo de arranque ejecuta ``lui gp, alto`` seguido de ``addiu gp, gp, bajo``. Leer el
        valor del propio ejecutable evita fijar una direccion en el codigo de la herramienta.

    Args:
        segmento (bytes): Segmento cargado del ejecutable.
        base (int): Direccion virtual del primer byte del segmento.
        codigo (tuple[int, int]): Rango ``[inicio, fin)`` donde buscar, alineado a 4 y dentro del segmento.

    Returns:
        int | None: El valor de ``$gp``, o ``None`` si el codigo no lo fija.

    Raises:
        ValueError: Si el rango esta desalineado o fuera del segmento.

    Ejemplo:
        gp = leer_gp(segmento, 0x80014A00, (0x80014A00, 0x8005DEA0))  # 0x80069320
    """
    inicio, fin = codigo
    if inicio % 4 or fin % 4 or inicio < base or fin > base + len(segmento) or inicio > fin:
        raise ValueError("datos pequenos: el rango de codigo debe estar alineado a 4 y dentro del segmento")
    for direccion in range(inicio, fin - 4, 4):
        (palabra,) = struct.unpack_from("<I", segmento, direccion - base)
        (siguiente,) = struct.unpack_from("<I", segmento, direccion + 4 - base)
        if _carga_alta(palabra) and _suma_baja(siguiente):
            bajo = siguiente & 0xFFFF
            bajo_con_signo = bajo - 0x10000 if bajo & 0x8000 else bajo
            return int((((palabra & 0xFFFF) << 16) + bajo_con_signo) & 0xFFFFFFFF)
    return None


def _carga_alta(palabra: int) -> bool:
    """``lui gp, alto``."""
    return palabra >> 26 == _LUI and (palabra >> 16) & 31 == REGISTRO_GP


def _suma_baja(palabra: int) -> bool:
    """``addiu gp, gp, bajo``."""
    return (
        palabra >> 26 == _ADDIU
        and (palabra >> 21) & 31 == REGISTRO_GP
        and (palabra >> 16) & 31 == REGISTRO_GP
    )


def descubrir_datos_pequenos(
    segmento: bytes, base: int, codigo: tuple[int, int], gp: int, limite: int
) -> list[Simbolo]:
    """
    Declara como datos las variables que el codigo direcciona con ``$gp``.

    Contexto:
        Cada desplazamiento distinto es una variable (o el inicio de un arreglo o estructura cuya
        direccion se toma con ``addiu reg, gp, desplazamiento``). El tamano es el ancho del acceso
        mas ancho (1, 2 o 4 bytes); un dato puede contener al siguiente cuando un acceso ancho abarca
        a otra variable (un campo dentro de una estructura). Si solo se toma la direccion, se usa la
        distancia al siguiente dato (con tope ``COTA_DIRECCION_TOMADA``), que es una cota superior y no
        el tamano real.

    Args:
        segmento (bytes): Segmento cargado del ejecutable.
        base (int): Direccion virtual del primer byte del segmento.
        codigo (tuple[int, int]): Rango ``[inicio, fin)`` del codigo que se recorre.
        gp (int): Valor de ``$gp`` (ver ``leer_gp``).
        limite (int): Primera direccion posterior a la ultima variable posible (fin del segmento).

    Returns:
        list[Simbolo]: Simbolos ``D_<direccion>`` en orden ascendente de direccion, de tipo ``u8``, ``u16``
        o ``u32`` segun el ancho del acceso (``u8`` tambien si solo se toma la direccion del dato).

    Raises:
        ValueError: Si el rango de codigo es invalido.

    Ejemplo:
        datos = descubrir_datos_pequenos(segmento, 0x80014A00, codigo, 0x80069320, 0x80069A00)
    """
    inicio, fin = codigo
    if inicio % 4 or fin % 4 or inicio < base or fin > base + len(segmento) or inicio > fin:
        raise ValueError("datos pequenos: el rango de codigo debe estar alineado a 4 y dentro del segmento")
    anchos: dict[int, int] = {}
    for direccion in range(inicio, fin, 4):
        (palabra,) = struct.unpack_from("<I", segmento, direccion - base)
        operacion, rs, rt = palabra >> 26, (palabra >> 21) & 31, (palabra >> 16) & 31
        if rs != REGISTRO_GP:
            continue
        desplazamiento = (palabra & 0xFFFF) - (0x10000 if palabra & 0x8000 else 0)
        if operacion in _ANCHO_POR_OPERACION:
            ancho = _ANCHO_POR_OPERACION[operacion]
        elif operacion == _ADDIU and rt != REGISTRO_GP:
            ancho = 0
        else:
            continue
        destino = gp + desplazamiento
        if base <= destino < limite:
            anchos[destino] = max(anchos.get(destino, 0), ancho)
    ordenadas = sorted(anchos)
    tipos = {1: "u8", 2: "u16", 4: "u32", 0: "u8"}
    simbolos: list[Simbolo] = []
    for indice, destino in enumerate(ordenadas):
        siguiente = ordenadas[indice + 1] if indice + 1 < len(ordenadas) else limite
        distancia = siguiente - destino
        ancho = anchos[destino]
        tamano = min(distancia, COTA_DIRECCION_TOMADA) if ancho == 0 else ancho
        simbolos.append(Simbolo(f"D_{destino:08X}", destino, cast(TipoSimbolo, tipos[ancho]), tamano))
    return simbolos
