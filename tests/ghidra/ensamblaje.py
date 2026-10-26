"""Codificacion de instrucciones MIPS para armar programas sinteticos en las pruebas."""

from collections.abc import Sequence

NOP = 0x00000000
T0, T1, V0, V1, AT, A0, RA = 8, 9, 2, 3, 1, 4, 31


def lui(rt: int, inmediato: int) -> int:
    return 0x3C000000 | rt << 16 | inmediato & 0xFFFF


def addiu(rt: int, rs: int, inmediato: int) -> int:
    return 0x24000000 | rs << 21 | rt << 16 | inmediato & 0xFFFF


def ori(rt: int, rs: int, inmediato: int) -> int:
    return 0x34000000 | rs << 21 | rt << 16 | inmediato & 0xFFFF


def sll(rd: int, rt: int, desplazamiento: int) -> int:
    return rt << 16 | rd << 11 | desplazamiento << 6


def add(rd: int, rs: int, rt: int) -> int:
    return rs << 21 | rt << 16 | rd << 11 | 0x20


def addu(rd: int, rs: int, rt: int) -> int:
    return rs << 21 | rt << 16 | rd << 11 | 0x21


def lw(rt: int, desplazamiento: int, rs: int) -> int:
    return 0x8C000000 | rs << 21 | rt << 16 | desplazamiento & 0xFFFF


def sw(rt: int, desplazamiento: int, rs: int) -> int:
    return 0xAC000000 | rs << 21 | rt << 16 | desplazamiento & 0xFFFF


def jr(rs: int) -> int:
    return rs << 21 | 0x08


def jalr(rs: int) -> int:
    return rs << 21 | RA << 11 | 0x09


def j(destino: int) -> int:
    return 0x08000000 | (destino >> 2) & 0x03FFFFFF


def beq(rs: int, rt: int, origen: int, destino: int) -> int:
    return 0x10000000 | rs << 21 | rt << 16 | ((destino - origen - 4) >> 2) & 0xFFFF


def bne(rs: int, rt: int, origen: int, destino: int) -> int:
    return 0x14000000 | rs << 21 | rt << 16 | ((destino - origen - 4) >> 2) & 0xFFFF


def retorno() -> list[int]:
    """``jr ra`` con su ranura de retardo vacia."""
    return [jr(RA), NOP]


def programa(direccion: int, palabras: Sequence[int]) -> dict[int, int]:
    """Palabras consecutivas desde ``direccion`` como mapa direccion a palabra."""
    return {direccion + 4 * i: palabra for i, palabra in enumerate(palabras)}
