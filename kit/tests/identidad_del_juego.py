"""Terminos que identifican a un juego concreto y que no pueden aparecer en el kit.

El kit es generico: ni su codigo, ni sus pruebas, ni su documentacion nombran el juego, su ejecutable,
sus funciones o la maquina donde se desarrollo. Esta lista es la unica definicion; la usan la prueba de
la ayuda de la linea de ordenes y la exploracion de todo el arbol.
"""

import re

TERMINOS_PROHIBIDOS: tuple[str, ...] = (
    "SLUS",
    "BBLIT",
    "bblit",
    "Bugs",
    "Bunny",
    "Lost in Time",
    "0fad70d9",
    "Ordi94N",
    "portarJuegos",
    "C:/Users",
    r"C:\Users",
    "src/",
    "config/",
    "NON_MATCHING",
)
"""Cadenas literales prohibidas en la ayuda de las ordenes (donde el manifiesto es la unica fuente)."""

PATRONES_PROHIBIDOS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bfunc_800[0-9A-Fa-f]{5}\b"),
    re.compile(r"\bD_800[0-9A-Fa-f]{5}\b"),
    re.compile(r"0x800[1-6][0-9A-Fa-f]{4}\b"),
)
"""Nombres automaticos y direcciones del espacio de codigo de un ejecutable real, en todo el kit."""
