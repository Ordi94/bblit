"""Reexportacion de ``psxdecomp.toolchain.plataforma`` con el alias de variables del proyecto."""

from functools import partial

from psxdecomp.entorno import SUFIJO_PREFIJO_BINUTILS, SUFIJO_WINE
from psxdecomp.toolchain import plataforma as _kit
from psxdecomp.toolchain.plataforma import (
    ALIAS_BINUTILS,
    EXTENSION_WINDOWS,
    PREFIJO_BINUTILS_NATIVO,
    WINE_POR_OMISION,
    buscar_sin_distinguir_mayusculas,
    entorno_proceso,
    es_ejecutable_windows,
    es_windows,
)
from tools.toolchain.contexto import VARIABLES

VARIABLE_WINE = VARIABLES.nombre_del_proyecto(SUFIJO_WINE)
VARIABLE_PREFIJO_BINUTILS = VARIABLES.nombre_del_proyecto(SUFIJO_PREFIJO_BINUTILS)

adaptar_comando = partial(_kit.adaptar_comando, variables=VARIABLES)
comando_wine = partial(_kit.comando_wine, variables=VARIABLES)
localizar_binutils = partial(_kit.localizar_binutils, variables=VARIABLES)
prefijo_binutils = partial(_kit.prefijo_binutils, variables=VARIABLES)

__all__ = [
    "ALIAS_BINUTILS",
    "EXTENSION_WINDOWS",
    "PREFIJO_BINUTILS_NATIVO",
    "VARIABLE_PREFIJO_BINUTILS",
    "VARIABLE_WINE",
    "WINE_POR_OMISION",
    "adaptar_comando",
    "buscar_sin_distinguir_mayusculas",
    "comando_wine",
    "entorno_proceso",
    "es_ejecutable_windows",
    "es_windows",
    "localizar_binutils",
    "prefijo_binutils",
]
