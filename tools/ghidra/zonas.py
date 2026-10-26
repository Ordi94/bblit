"""Zonas del segmento de codigo del ejecutable y su clasificacion.

El segmento cargado en ``0x80014A00`` se reparte en codigo de arranque del SDK, codigo propio del
juego, codigo de las librerias de Sony y, a continuacion, datos. Los limites salen de
``docs/MAPA_MEMORIA.md``: son exactos porque coinciden con inicios de funcion de la tabla de
simbolos, y los demas modulos de analisis los comparten desde aqui para no duplicar constantes.
"""

from typing import Final, Literal

from tools.ghidra.dominio import DIRECCION_BASE, FIN_CODIGO

INICIO_JUEGO: Final[int] = 0x80014AC4
"""Primera direccion del codigo propio del juego (tras las rutinas de arranque del SDK)."""

FIN_JUEGO: Final[int] = 0x80045DA0
"""Primera direccion del codigo de las librerias de Sony (fin exclusivo del codigo del juego)."""

ClaseZona = Literal["arranque", "juego", "libreria", "externo"]
"""Clase de una direccion: rutinas de arranque, juego, libreria de Sony o fuera del segmento."""


def clasificar_zona(direccion: int) -> ClaseZona:
    """
    Indica a que zona del segmento pertenece una direccion de codigo.

    Contexto:
        Lo usan el grafo de llamadas (para etiquetar si el destino de una llamada es del juego
        o de una libreria) y la seleccion de funciones para los borradores.

    Args:
        direccion (int): Direccion virtual.

    Returns:
        ClaseZona: ``arranque`` en ``[0x80014A00, 0x80014AC4)``, ``juego`` hasta
        ``0x80045DA0``, ``libreria`` hasta el fin del codigo (``0x8005DEA0``) y ``externo``
        para cualquier otra direccion (RAM previa al segmento, datos, BIOS).

    Ejemplo:
        clase = clasificar_zona(0x80016414)  # "juego"
    """
    if DIRECCION_BASE <= direccion < INICIO_JUEGO:
        return "arranque"
    if INICIO_JUEGO <= direccion < FIN_JUEGO:
        return "juego"
    if FIN_JUEGO <= direccion < FIN_CODIGO:
        return "libreria"
    return "externo"


INICIO_ESTADO: Final[int] = 0x80010000
INICIO_DATOS: Final[int] = FIN_CODIGO
INICIO_DATOS_PEQUENOS: Final[int] = 0x80069000
INICIO_BSS: Final[int] = 0x80069348
FIN_BSS: Final[int] = 0x800768A8

REGIONES_DATOS: Final[tuple[tuple[str, int, int], ...]] = (
    ("scratchpad", 0x1F800000, 0x1F800400),
    ("hardware", 0x1F801000, 0x1F803000),
    ("estado_global", INICIO_ESTADO, DIRECCION_BASE),
    ("codigo_y_literales", DIRECCION_BASE, INICIO_DATOS),
    ("datos_y_tablas", INICIO_DATOS, 0x80067800),
    ("cadenas_y_mensajes", 0x80067800, INICIO_DATOS_PEQUENOS),
    ("datos_pequenos", INICIO_DATOS_PEQUENOS, INICIO_BSS),
    ("bss", INICIO_BSS, FIN_BSS),
    ("heap", FIN_BSS, 0x80200000),
)
"""Regiones de datos de ``docs/MAPA_MEMORIA.md`` como ``(nombre, inicio, fin_exclusivo)``."""


def region_de_dato(direccion: int) -> str:
    """
    Indica a que region de datos pertenece una direccion.

    Contexto:
        Resume que partes de la memoria toca cada subsistema (estado global, tablas, cadenas,
        datos pequenos accedidos con ``$gp``, bss) al caracterizarlo.

    Args:
        direccion (int): Direccion virtual de un dato.

    Returns:
        str: Nombre de la region de ``REGIONES_DATOS`` o ``otra`` si no cae en ninguna.

    Ejemplo:
        region = region_de_dato(0x80010000)  # "estado_global"
    """
    for nombre, inicio, fin in REGIONES_DATOS:
        if inicio <= direccion < fin:
            return nombre
    return "otra"
