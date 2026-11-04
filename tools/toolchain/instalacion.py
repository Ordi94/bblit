"""Reexportacion de ``psxdecomp.toolchain.instalacion`` con el alias de variables del proyecto."""

from functools import partial

from psxdecomp.toolchain import instalacion as _kit
from psxdecomp.toolchain.instalacion import (
    CARPETA_DESCARGA,
    MAX_BYTES_LOCK,
    NOMBRE_MARCA,
    carpeta_componente,
    esta_instalado,
    faltantes,
    instalar,
    instalar_componente,
    leer_lock,
)
from tools.toolchain.contexto import VARIABLES

resolver_herramienta = partial(_kit.resolver_herramienta, variables=VARIABLES)

__all__ = [
    "CARPETA_DESCARGA",
    "MAX_BYTES_LOCK",
    "NOMBRE_MARCA",
    "carpeta_componente",
    "esta_instalado",
    "faltantes",
    "instalar",
    "instalar_componente",
    "leer_lock",
    "resolver_herramienta",
]
