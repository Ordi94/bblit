"""Lectura acotada del segmento de codigo del ejecutable PS-X EXE.

La validacion de funciones necesita mirar las instrucciones reales: un nombre y un tamano de
Ghidra no bastan para distinguir una funcion de un fragmento interior de otra. Este modulo
solo lee y comprueba cotas; las decisiones viven en ``dominio``.
"""

from pathlib import Path
from typing import Final

import rabbitizer

from tools.ghidra.dominio import DIRECCION_BASE, DIRECCION_FIN, TAMANO_SEGMENTO

TAMANO_CABECERA: Final[int] = 0x800
"""Bytes de la cabecera PS-X EXE que preceden al segmento."""

FIRMA_PSX: Final[bytes] = b"PS-X EXE"


def leer_segmento(ruta: Path) -> bytes:
    """
    Lee el segmento cargado de un ejecutable PS-X EXE.

    Contexto:
        Entrada del comando ``simbolos``: las palabras devueltas se usan para validar que cada
        funcion candidata sea codigo completo.

    Args:
        ruta (Path): Ruta del ejecutable.

    Returns:
        bytes: Los ``TAMANO_SEGMENTO`` bytes que se cargan desde ``DIRECCION_BASE``.

    Raises:
        ValueError: Si el archivo no empieza por la firma ``PS-X EXE`` o su tamano no es el
            de la cabecera mas el segmento.
        FileNotFoundError: Si la ruta no existe.

    Ejemplo:
        segmento = leer_segmento(Path("SLUS_008.38"))
    """
    esperado = TAMANO_CABECERA + TAMANO_SEGMENTO
    if ruta.stat().st_size != esperado:
        raise ValueError(f"ejecutable: el tamano debe ser {esperado} bytes")
    datos = ruta.read_bytes()
    if not datos.startswith(FIRMA_PSX):
        raise ValueError("ejecutable: falta la firma PS-X EXE")
    return datos[TAMANO_CABECERA:]


def palabra_en(segmento: bytes, direccion: int) -> int:
    """
    Devuelve la palabra de 32 bits (little endian) en una direccion del segmento.

    Contexto:
        Acceso usado por la validacion de funciones; comprueba cotas para no leer fuera.

    Args:
        segmento (bytes): Resultado de ``leer_segmento``.
        direccion (int): Direccion alineada a 4 dentro del segmento.

    Returns:
        int: La palabra sin signo.

    Raises:
        ValueError: Si la direccion esta fuera del segmento, no esta alineada o el segmento
            no tiene el tamano esperado.

    Ejemplo:
        instruccion = palabra_en(segmento, 0x80014A00)
    """
    if len(segmento) != TAMANO_SEGMENTO:
        raise ValueError(f"segmento: el tamano debe ser {TAMANO_SEGMENTO} bytes")
    if not DIRECCION_BASE <= direccion < DIRECCION_FIN or direccion % 4 != 0:
        raise ValueError(f"direccion 0x{direccion:08X} fuera del segmento o no alineada")
    inicio = direccion - DIRECCION_BASE
    return int.from_bytes(segmento[inicio : inicio + 4], "little")


def instruccion_valida(instruccion: int, direccion: int) -> bool:
    """
    Indica si una palabra decodifica como instruccion MIPS valida.

    Contexto:
        Distingue el codigo de las tablas de datos incrustadas entre funciones al decidir si un
        hueco sin funcion empieza una rutina.

    Args:
        instruccion (int): Palabra de 32 bits.
        direccion (int): Direccion virtual de la palabra (algunas instrucciones dependen de ella).

    Returns:
        bool: Verdadero si el desensamblador la reconoce.

    Ejemplo:
        instruccion_valida(0x03E00008, 0x80014A00)  # True
    """
    return bool(rabbitizer.Instruction(instruccion, direccion).isValid())
