"""Segmentos de ejecutable sinteticos para probar la validacion de funciones."""

from pathlib import Path

JR_RA = 0x03E00008
SALTO = 0x08000000
NOP = 0x00000000
INSTRUCCION = 0x24020001
"""``addiu v0,zero,1``: una instruccion cualquiera que decodifica como valida."""
DATO = 0x00200000
"""Palabra que no decodifica como instruccion (dato incrustado)."""

BASE = 0x80014A00


def segmento(palabras: dict[int, int]) -> bytes:
    """Construye un segmento de ceros con las palabras indicadas (clave: direccion virtual)."""
    datos = bytearray(0x55000)
    for direccion, palabra in palabras.items():
        inicio = direccion - BASE
        datos[inicio : inicio + 4] = palabra.to_bytes(4, "little")
    return bytes(datos)


def cierre(direccion: int, tamano: int) -> dict[int, int]:
    """Palabras de una funcion que termina en ``jr ra`` con su ranura al final del cuerpo."""
    return {direccion + tamano - 8: JR_RA}


def escribir_ejecutable(ruta: Path, palabras: dict[int, int]) -> Path:
    """Escribe un PS-X EXE sintetico: cabecera de 0x800 bytes y el segmento indicado."""
    cabecera = b"PS-X EXE" + bytes(0x800 - 8)
    ruta.write_bytes(cabecera + segmento(palabras))
    return ruta
