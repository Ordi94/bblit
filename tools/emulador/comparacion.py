"""
Lectura de volcados y archivos para el comando `comparar`.

Contexto:
    Capa de servicio de `tools.emulador`: lee del disco con cotas de tamano y delega la
    comparacion en las reglas puras de `dominio`. Nunca escribe.
"""

from __future__ import annotations

from pathlib import Path

from tools.emulador.dominio import (
    RAM_FIN,
    ResultadoComparacion,
    comparar_regiones,
    offset_de_ram,
    validar_ram,
)


def leer_volcado(ruta: Path) -> bytes:
    """
    Lee un volcado de RAM y comprueba que tiene el tamano exacto.

    Contexto:
        Entrada de `comparar`; el volcado procede de `volcar`, `sesion` o de un archivo
        ajeno, asi que se valida antes de usarlo.

    Args:
        ruta (Path): Archivo del volcado.

    Returns:
        bytes: Los 2.097.152 bytes del volcado.

    Raises:
        ValueError: Si el tamano no es el de la RAM.
        OSError: Si el archivo no se puede leer.

    Ejemplo:
        ram = leer_volcado(Path("ram.bin"))
    """
    return validar_ram(ruta.read_bytes())


def _leer_trozo(ruta: Path, desde: int, largo: int) -> bytes:
    """
    Lee como maximo `largo` bytes de un archivo a partir de `desde`.

    Contexto:
        Acota la lectura al tamano de la RAM, de modo que un archivo enorme no se carga entero.

    Args:
        ruta (Path): Archivo a leer.
        desde (int): Offset inicial dentro del archivo.
        largo (int): Maximo de bytes a leer.

    Returns:
        bytes: Los bytes leidos (menos de `largo` si el archivo termina antes).

    Raises:
        ValueError: Si `desde` es negativo o esta mas alla del final del archivo.
        OSError: Si el archivo no se puede leer.

    Ejemplo:
        datos = _leer_trozo(Path("SLUS_008.38"), 0x800, 0x55000)
    """
    if desde < 0:
        raise ValueError(f"offset del archivo {desde}: se esperaba un valor mayor o igual a 0")
    tamano = ruta.stat().st_size
    if desde > tamano:
        raise ValueError(f"offset del archivo 0x{desde:X}: sobrepasa el tamano del archivo ({tamano} bytes)")
    with ruta.open("rb") as archivo:
        archivo.seek(desde)
        return archivo.read(largo)


def comparar_con_archivo(
    volcado: Path,
    direccion: int,
    archivo: Path,
    offset_archivo: int = 0,
    longitud: int | None = None,
) -> ResultadoComparacion:
    """
    Compara una region del volcado con el contenido de un archivo.

    Contexto:
        Caso tipico: el segmento de codigo del ejecutable (`0x80014A00`, a partir del offset
        `0x800` del archivo) contra lo que hay en memoria.

    Args:
        volcado (Path): Volcado de RAM de 2.097.152 bytes.
        direccion (int): Direccion de consola donde empieza la region.
        archivo (Path): Archivo con el que comparar.
        offset_archivo (int, opcional): Offset dentro del archivo donde empieza la region.
        longitud (int, opcional): Bytes a comparar; por defecto todo lo disponible en ambos.

    Returns:
        ResultadoComparacion: Conteos y primer offset distinto.

    Raises:
        ValueError: Si el volcado, la direccion, la longitud o el offset son invalidos.
        OSError: Si algun archivo no se puede leer.

    Ejemplo:
        resultado = comparar_con_archivo(Path("ram.bin"), 0x80014A00, Path("SLUS_008.38"), 0x800)
    """
    ram = leer_volcado(volcado)
    inicio = offset_de_ram(direccion, longitud or 0)
    largo = RAM_FIN - direccion if longitud is None else longitud
    del_archivo = _leer_trozo(archivo, offset_archivo, largo)
    # Sin longitud explicita se compara lo que el archivo aporta; asi un ejecutable mas corto
    # que el resto de la RAM no se reporta como "tamano distinto" por la cola sin cargar.
    fin = inicio + (len(del_archivo) if longitud is None else largo)
    return comparar_regiones(direccion, ram[inicio:fin], del_archivo)


def comparar_volcados(
    volcado_a: Path, volcado_b: Path, direccion: int, longitud: int | None = None
) -> ResultadoComparacion:
    """
    Compara la misma region de dos volcados de RAM.

    Contexto:
        Sirve para ver que cambia entre dos momentos del juego (por ejemplo titulo y nivel).

    Args:
        volcado_a (Path): Primer volcado.
        volcado_b (Path): Segundo volcado.
        direccion (int): Direccion de consola donde empieza la region.
        longitud (int, opcional): Bytes a comparar; por defecto hasta el final de la RAM.

    Returns:
        ResultadoComparacion: Conteos y primer offset distinto.

    Raises:
        ValueError: Si algun volcado, la direccion o la longitud son invalidos.
        OSError: Si algun archivo no se puede leer.

    Ejemplo:
        resultado = comparar_volcados(Path("a.bin"), Path("b.bin"), 0x80000000)
    """
    ram_a = leer_volcado(volcado_a)
    ram_b = leer_volcado(volcado_b)
    inicio = offset_de_ram(direccion, longitud or 0)
    fin = inicio + (RAM_FIN - direccion if longitud is None else longitud)
    return comparar_regiones(direccion, ram_a[inicio:fin], ram_b[inicio:fin])
